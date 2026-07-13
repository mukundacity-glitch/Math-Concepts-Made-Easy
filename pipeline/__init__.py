"""Math Concepts Made Easy — automated lesson production pipeline.

Stages (each is an independently runnable module):
  cell1_lesson     lesson data + 9-scene narrations → cell1_config.py
  cell2_script     master script JSON (scenes, timings, board actions)
  cell3_audio      Edge-TTS narration + word boundaries per scene
  cell4_animation  Manim renders one MP4 per scene
  cell5_assembly   mux audio+video, crossfade, final MP4
  cell6_thumbnail  cinematic 1080p thumbnail
  cell7_shorts     vertical 1080x1920 YouTube Short
  cell8_subtitles  SRT + VTT captions from Edge-TTS word timings

Run everything for the next scheduled day with:  python autopilot.py
"""
