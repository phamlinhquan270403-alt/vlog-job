---
name: learn-vlog
description: Học style edit từ video/kênh/playlist YouTube vlog. Máy tải và đo nhịp, Gemini nghe âm thanh, Haiku (API) đọc contact sheet, còn phần phân tích và viết style guide do Claude Code (gói Pro) tự làm. Cập nhật docs/edit-recipe.md.
argument-hint: "<link video | link kênh | link playlist> [link khác...]"
---

Trả lời người dùng bằng tiếng Việt. API key chỉ dùng **Haiku** để đọc ảnh. Không gọi Sonnet/Opus qua API
(script đã chặn). Phần phân tích là việc của chính phiên Claude Code này.

1. **Chọn video.** Link kênh/playlist thì liệt kê bằng
   `py -m yt_dlp --flat-playlist --playlist-end 30 --print "%(id)s | %(duration_string)s | %(view_count)s | %(title)s" <link>`
   rồi chọn 3 video: 2 nhiều view nhất + 1 mới nhất, bỏ qua video không cùng thể loại. Nói người dùng đã chọn video nào.
2. **Đo trên máy (miễn phí):** chạy song song mỗi video
   `py tools/watch_video.py <link>`. Kết quả là `reference/youtube/<id>/report.md`, gồm nhịp cắt, timeline và transcript.
   Video đã có thì không tải lại.
3. **Gemini nghe âm thanh:** `sh tools/run_gemini_all.sh` (chạy nền). Đoạn nào xong rồi thì bỏ qua.
   Key xoay vòng theo `.env`. Nếu tất cả key hết quota ngày thì báo người dùng thêm key ở project mới, hoặc chờ reset (~15:00 giờ VN).
4. **Haiku đọc contact sheet:** `py tools/claude_read.py sheets <id...>` (khoảng $0.04/video), tạo ra
   `claude_visual_log.md` mỗi video. **Không** Read từng `sheets/*.jpg` trong phiên.
5. **Phân tích (gói Pro), mỗi video một file `reference/youtube/<id>/claude_visual.md`:**
   - Đọc phần đầu `report.md` (số liệu), các mục `### Chunk` của Gemini (dùng phần summary, chỉ xem event khi cần), và `claude_visual_log.md`.
   - Transcript dài thì Grep theo mốc thời gian, không đọc hết.
   - Viết theo các mục: Cấu trúc, Hình ảnh, Chữ trên màn hình, Chuyển cảnh và hiệu ứng, Âm thanh, Công thức làm lại.
     Dẫn mốc thời gian làm bằng chứng, chỉ ghi điều dữ liệu cho thấy.
   - Chữ quan trọng (title, handle, nhãn) và claim lạ của Gemini: cắt đúng frame để kiểm
     (`ffmpeg -ss <giây> -i video.mp4 -frames:v 1 -vf scale=640:-2 work/frames/x.jpg`, ghép vài frame bằng PIL rồi Read một lần).
     Haiku hay đọc sai chữ nhỏ (ví dụ @apinvy → @opinvy).
6. **Cập nhật `docs/edit-recipe.md`:**
   - Mẫu của một kênh phải thấy ở ≥2/3 video của kênh đó, ghi kèm video làm bằng chứng.
   - Mẫu thấy ở ≥2 kênh thì đưa vào mục "Mẫu chung của thể loại".
   - Thứ chỉ một video làm thì đưa vào mục "Dấu riêng".
   - Thêm vào mục "Chỗ các nguồn mâu thuẫn" khi dữ liệu mới trái với dữ liệu cũ.
   - Giữ file gọn, gộp những ý trùng nhau.
7. **Báo người dùng:**
   - Nhịp từng video (vài dòng).
   - Mẫu nào mới lên mức "chung" hoặc mức kênh.
   - Những gì đã đổi trong `edit-recipe.md`.
   - Tiền API đã tiêu (`py tools/claude_read.py cost`) và tình trạng quota Gemini.
