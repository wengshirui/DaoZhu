use std::process::{Child, Command};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Mutex;
use std::thread;
use std::time::Duration;
use std::fs;
use std::path::PathBuf;

use serde::{Deserialize, Serialize};
use tauri::{
    menu::{MenuBuilder, MenuItemBuilder},
    tray::TrayIconBuilder,
    webview::WebviewWindowBuilder,
    Manager, RunEvent, WindowEvent,
};
use tauri_plugin_global_shortcut::GlobalShortcutExt;

/// 全局持有 Python 后端子进程
struct BackendProcess(Mutex<Option<Child>>);

/// 是否真正退出
static SHOULD_EXIT: AtomicBool = AtomicBool::new(false);

/// 窗口状态（位置/大小记忆）
#[derive(Serialize, Deserialize, Default)]
struct WindowState {
    x: Option<f64>,
    y: Option<f64>,
    width: Option<f64>,
    height: Option<f64>,
}

fn state_file_path() -> PathBuf {
    let mut path = std::env::current_dir().unwrap_or_default();
    path.push(".window_state.json");
    path
}

fn load_window_state() -> Option<WindowState> {
    let path = state_file_path();
    let content = fs::read_to_string(path).ok()?;
    serde_json::from_str(&content).ok()
}

fn save_window_state(state: &WindowState) {
    let path = state_file_path();
    if let Ok(json) = serde_json::to_string(state) {
        let _ = fs::write(path, json);
    }
}

/// Tauri 命令：在系统浏览器中打开 URL
#[tauri::command]
fn open_external(url: String) {
    let _ = open::that(&url);
}

/// Tauri 命令：切换窗口置顶
#[tauri::command]
fn toggle_always_on_top(window: tauri::Window) -> bool {
    let current = window.is_always_on_top().unwrap_or(false);
    let _ = window.set_always_on_top(!current);
    !current
}

/// Tauri 命令：显示主窗口（宠物双击调用）
#[tauri::command]
fn show_main_window(app: tauri::AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        // Windows 上隐藏窗口需要完整的恢复流程
        let _ = window.unminimize();
        let _ = window.show();
        let _ = window.set_focus();
    }
}

/// Tauri 命令：开始拖拽窗口（宠物窗口拖拽）
#[tauri::command]
fn start_dragging(window: tauri::Window) {
    let _ = window.start_dragging();
}

/// 启动 Python 后端 (uvicorn)
fn start_backend(port: u16) -> Option<Child> {
    let python_candidates = vec![
        ".venv/Scripts/python.exe",
        ".venv/bin/python",
        "python",
    ];

    for python in &python_candidates {
        let result = Command::new(python)
            .args([
                "-m", "uvicorn",
                "daozhu.app:app",
                "--host", "127.0.0.1",
                "--port", &port.to_string(),
                "--log-level", "warning",
            ])
            .spawn();

        if let Ok(child) = result {
            log::info!("后端启动成功: {} (PID: {})", python, child.id());
            return Some(child);
        }
    }

    log::error!("无法启动 Python 后端");
    None
}

/// 等待后端就绪
fn wait_for_backend(port: u16, timeout_secs: u64) -> bool {
    let url = format!("http://127.0.0.1:{}", port);
    let client = reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(2))
        .redirect(reqwest::redirect::Policy::none())
        .build()
        .unwrap();

    for _ in 0..timeout_secs {
        if let Ok(resp) = client.get(&url).send() {
            if resp.status().as_u16() < 500 {
                log::info!("后端就绪: {}", url);
                return true;
            }
        }
        thread::sleep(Duration::from_secs(1));
    }

    log::error!("后端超时未就绪 ({}s)", timeout_secs);
    false
}

/// 优雅关闭后端子进程
fn stop_backend(state: &BackendProcess) {
    if let Ok(mut guard) = state.0.lock() {
        if let Some(ref mut child) = *guard {
            log::info!("正在关闭后端进程 (PID: {})", child.id());
            let _ = child.kill();
            let _ = child.wait();
        }
        *guard = None;
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let port: u16 = 7788;

    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            // 第二个实例启动时 → 显示已有实例的主窗口
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.unminimize();
                let _ = window.show();
                let _ = window.set_focus();
            }
        }))
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .plugin(
            tauri_plugin_log::Builder::default()
                .level(log::LevelFilter::Info)
                .build(),
        )
        .manage(BackendProcess(Mutex::new(None)))
        .invoke_handler(tauri::generate_handler![open_external, toggle_always_on_top, show_main_window, start_dragging])
        .setup(move |app| {
            let app_handle = app.handle().clone();

            // --- 全局快捷键 Ctrl+Alt+D：呼出/隐藏窗口 ---
            use tauri_plugin_global_shortcut::ShortcutState;
            app.global_shortcut().on_shortcut("Ctrl+Alt+D", move |app, _shortcut, event| {
                if event.state == ShortcutState::Pressed {
                    if let Some(window) = app.get_webview_window("main") {
                        let visible = window.is_visible().unwrap_or(false);
                        let minimized = window.is_minimized().unwrap_or(false);
                        let focused = window.is_focused().unwrap_or(false);

                        // 只有窗口可见 + 未最小化 + 有焦点时才隐藏
                        if visible && !minimized && focused {
                            let _ = window.hide();
                        } else {
                            let _ = window.unminimize();
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                }
            })?;

            // --- 手动创建主窗口（带 on_navigation 拦截外部链接）---
            let main_url = format!("http://localhost:{}", port);
            let main_url_clone = main_url.clone();

            // 先显示 loading 页（后端还没启动时显示本地 loading.html）
            let loading_url = format!("http://localhost:{}/loading.html", port);
            let initial_url = tauri::WebviewUrl::External(loading_url.parse().unwrap_or_else(|_| {
                "about:blank".parse().unwrap()
            }));

            // 恢复上次窗口位置/大小
            let saved = load_window_state();
            let width = saved.as_ref().and_then(|s| s.width).unwrap_or(1080.0);
            let height = saved.as_ref().and_then(|s| s.height).unwrap_or(650.0);

            let mut builder = WebviewWindowBuilder::new(app, "main", initial_url)
                .title("岛主 DaoZhu")
                .inner_size(width, height)
                .min_inner_size(800.0, 500.0)
                .visible(true)
                .on_navigation(move |url| {
                    let url_str = url.as_str();
                    // 允许主服务所有路径
                    if url_str.starts_with(&main_url_clone) {
                        return true;
                    }
                    // 允许 about:blank
                    if url_str == "about:blank" {
                        return true;
                    }
                    // 其他链接阻止（由前端 window.open 覆盖处理）
                    false
                });

            // 恢复上次位置（如有保存）
            if let Some(ref state) = saved {
                if let (Some(x), Some(y)) = (state.x, state.y) {
                    builder = builder.position(x, y);
                }
            } else {
                builder = builder.center();
            }

            builder.build()?;

            // --- 系统托盘 ---
            let show_item = MenuItemBuilder::with_id("show", "显示主窗口").build(app)?;
            let pin_item = MenuItemBuilder::with_id("pin", "窗口置顶").build(app)?;
            let pet_item = MenuItemBuilder::with_id("pet", "显示/隐藏宠物").build(app)?;
            let quit_item = MenuItemBuilder::with_id("quit", "退出").build(app)?;
            let tray_menu = MenuBuilder::new(app)
                .item(&show_item)
                .item(&pin_item)
                .separator()
                .item(&pet_item)
                .separator()
                .item(&quit_item)
                .build()?;

            let icon_bytes = include_bytes!("../icons/32x32.png");
            let icon = tauri::image::Image::from_bytes(icon_bytes)
                .expect("无法加载托盘图标");

            TrayIconBuilder::new()
                .icon(icon)
                .menu(&tray_menu)
                .tooltip("岛主 DaoZhu")
                .on_menu_event(move |app, event| match event.id().as_ref() {
                    "show" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.unminimize();
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                    "pin" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let current = window.is_always_on_top().unwrap_or(false);
                            let _ = window.set_always_on_top(!current);
                            let _ = window.unminimize();
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                    "pet" => {
                        if let Some(pet_win) = app.get_webview_window("pet") {
                            if pet_win.is_visible().unwrap_or(false) {
                                let _ = pet_win.hide();
                            } else {
                                let _ = pet_win.show();
                            }
                        }
                    }
                    "quit" => {
                        SHOULD_EXIT.store(true, Ordering::SeqCst);
                        let state = app.state::<BackendProcess>();
                        stop_backend(&state);
                        app.exit(0);
                    }
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let tauri::tray::TrayIconEvent::DoubleClick { .. } = event {
                        let app = tray.app_handle();
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.unminimize();
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                })
                .build(app)?;

            // --- 启动后端（子线程）---
            let handle_for_backend = app_handle.clone();
            thread::spawn(move || {
                if let Some(child) = start_backend(port) {
                    let state = handle_for_backend.state::<BackendProcess>();
                    let mut guard = state.0.lock().unwrap();
                    *guard = Some(child);
                    drop(guard);
                }

                // 等待后端就绪 → 导航到主界面 + 创建宠物窗口
                if wait_for_backend(port, 30) {
                    if let Some(window) = handle_for_backend.get_webview_window("main") {
                        let url = format!("http://localhost:{}", port);
                        let _ = window.navigate(url.parse().unwrap());
                    }

                    // 创建桌面宠物透明窗口
                    let pet_url = format!("http://localhost:{}/pet.html", port);
                    let _ = WebviewWindowBuilder::new(
                        &handle_for_backend,
                        "pet",
                        tauri::WebviewUrl::External(pet_url.parse().unwrap()),
                    )
                    .title("桌面宠物")
                    .inner_size(130.0, 140.0)
                    .resizable(false)
                    .decorations(false)
                    .transparent(true)
                    .always_on_top(true)
                    .skip_taskbar(true)
                    .shadow(false)
                    .position(
                        (handle_for_backend.get_webview_window("main")
                            .and_then(|w| w.outer_position().ok())
                            .map(|p| p.x as f64)
                            .unwrap_or(800.0)) + 200.0,
                        100.0,
                    )
                    .build();
                }
            });

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("启动岛主失败")
        .run(|app, event| match event {
            RunEvent::WindowEvent { label, event, .. } => {
                if label == "main" {
                    if let WindowEvent::CloseRequested { api, .. } = event {
                        // 保存窗口位置/大小
                        if let Some(window) = app.get_webview_window("main") {
                            if let (Ok(pos), Ok(size)) = (window.outer_position(), window.inner_size()) {
                                let state = WindowState {
                                    x: Some(pos.x as f64),
                                    y: Some(pos.y as f64),
                                    width: Some(size.width as f64),
                                    height: Some(size.height as f64),
                                };
                                save_window_state(&state);
                            }
                            api.prevent_close();
                            let _ = window.hide();
                        }
                    }
                }
            }
            RunEvent::ExitRequested { api, .. } => {
                if !SHOULD_EXIT.load(Ordering::SeqCst) {
                    api.prevent_exit();
                }
            }
            RunEvent::Exit => {
                let state = app.state::<BackendProcess>();
                stop_backend(&state);
            }
            _ => {}
        });
}
