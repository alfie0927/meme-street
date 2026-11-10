Meme Street November reels
Copy this whole folder to D:\stock_market_sim\tools\november_reels

Each reel has:
  <date>_<time>_<id>.mp4          the video (1080x1920, 30fps, with voiceover)
  <date>_<time>_<id>.caption.txt  the Instagram caption, ready to paste
  <date>_<time>_<id>.srt          subtitles (optional)

schedule.csv / schedule.json list every post in order:
  post_at      ISO time with UTC offset (UK = GMT in November, so +00:00)
  video        file name
  caption_file caption file name
  ready        'yes' if the video is in this folder, 'rendering' if it's still being made
Times: 06:00, 12:00 and 18:00 UK time, every day.
