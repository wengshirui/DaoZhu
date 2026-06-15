"""
火柴人剧场 — 分镜数据结构（#083）
参考: Pixelle-Video models/storyboard.py

分镜是流水线各阶段间的契约：
- Stage 1（导演分析）输出分镜
- Stage 2（资产生成）填充 audio/image 字段
- Stage 3（动画渲染）填充 video_segment
- Stage 4（合成）消费全部字段
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CharacterConfig:
    """角色配置（由导演 LLM 生成）"""
    name: str
    gender: str = ""           # male / female
    voice_id: str = ""         # 指定音色（可选）
    color: str = "#333333"     # 火柴人颜色


@dataclass
class StoryboardFrame:
    """单帧分镜"""
    index: int                              # 帧序号
    narration: str = ""                     # 旁白/对话文字
    speaker: str = ""                       # 说话者（角色名 or "narrator"）
    characters: list = field(default_factory=list)  # 角色列表（位置/动作/表情）
    mood_tag: str = ""                      # 氛围标签（欢快/悲伤/紧张/温馨/史诗）
    image_prompt: str = ""                  # 场景背景图 prompt
    search_term: str = ""                   # Pexels 视频搜索关键词（英文 1-3 词）

    # Stage 2 填充
    audio_path: Optional[str] = None        # TTS 音频路径
    image_path: Optional[str] = None        # GLM-Image 背景图路径
    bgm_tag: str = ""                       # 匹配的 BGM 标签

    # Stage 3 填充
    duration: float = 0.0                   # 帧时长（秒，由 TTS 决定）
    video_segment: Optional[str] = None     # 该帧视频片段路径


@dataclass
class Storyboard:
    """完整分镜"""
    title: str
    frames: list[StoryboardFrame] = field(default_factory=list)
    characters: list[CharacterConfig] = field(default_factory=list)
    resolution: str = "1920x1080"           # 输出分辨率
    fps: int = 30

    # 最终输出
    final_video: Optional[str] = None
    total_duration: float = 0.0

    @property
    def progress(self) -> float:
        """当前完成度"""
        if not self.frames:
            return 0.0
        done = sum(1 for f in self.frames if f.video_segment)
        return done / len(self.frames)

    @property
    def is_complete(self) -> bool:
        return all(f.video_segment for f in self.frames)
