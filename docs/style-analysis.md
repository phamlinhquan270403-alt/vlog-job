# Phân tích style edit: Elena Taber vs apinvy (hà vy)

> Bản dùng để dựng là **[edit-recipe.md](edit-recipe.md)**: chỉ giữ mẫu lặp lại ở ≥2/3 video, có checklist dựng,
> và mục "Chỗ các nguồn mâu thuẫn" sửa vài nhận định bên dưới (ví dụ: Elena có phụ đề thoại ở Silk Road;
> Vy có voiceover trên b-roll; nhãn địa điểm của Vy không cố định góc trên trái).
> Style guide chi tiết từng video: `reference/youtube/<id>/claude_visual.md`.

Mẫu: 3 video mỗi kênh, chạy qua `tools/watch_video.py` (cắt shot ffmpeg ngưỡng 0.25, contact sheet, phụ đề YouTube).
Dữ liệu gốc ở `reference/youtube/<id>/report.md` và `sheets/`.

| Kênh | Video | Dài | Shot/phút | Shot trung vị | 15s đầu | 60s đầu |
|---|---|---|---|---|---|---|
| Elena | 6QvxeCFJf2I Silk Road | 19.8p | 27 | 1.45s | 25 shot | 44 |
| Elena | Xg5-vOi3ZDI Dolomites | 17.9p | 17 | 1.65s | 16 | 34 |
| Elena | hI0zwp6otwA Kilimanjaro | 26.7p | 18 | ~1.6s | 14 | 36 |
| Vy | VlG8fS9bb-4 Thượng Hải | 44.0p | 14 | 2.27s | 26 | 48 |
| Vy | pjIWt5y4O9s Hà Nội 5 ngày | 44.6p | 11 | 2.75s | 14 | 16 |
| Vy | 5yi4W05WyZY Phú Quốc | 23.4p | 9 | 3.09s | 2 | 13 |

Phần lời phủ: Elena ~77% thời lượng có lời, Vy ~95%. Vy nói gần như liên tục, Elena chừa nhiều đoạn chỉ có nhạc + b-roll.

---

## 1. Elena Taber: "documentary điện ảnh"

**Cấu trúc**
1. **0:00–0:25 cold open montage, không lời, chỉ nhạc.** Shot 0.3–0.5s, cắt theo beat. Silk Road mở bằng chuỗi *match-on-action*: cùng một dáng đi bộ ngang khung, đổi địa điểm mỗi beat (yurt → thánh đường → chợ → núi đỏ), chữ to "SILK ROAD" đứng yên đè lên. Sau đó là tràng b-roll đẹp nhất của cả chuyến (drone, chợ, người địa phương, chim ưng, núi) khoảng 0.3s/shot.
2. **Title card kiểu phim tài liệu:** chữ serif mảnh trắng, chữ hoa giãn ("MOUNT KILIMANJARO", "THE ITALIAN DOLOMITES"), kèm dòng tọa độ GPS nhỏ + 2–3 dòng mô tả kiểu bách khoa. Chữ hiện dần/trượt chậm trên drone shot.
3. **Flash đen ngắn → ngồi nói chuyện trước camera (~1 phút):** đang ở đâu, vì sao đi, kế hoạch mấy ngày. Có câu giữ người xem ("cuối video có giải thích hết cách mình tự lên lộ trình") rồi chốt "let's go".
4. **Thân video:** xen kẽ (a) đoạn montage b-roll 1–1.5s/shot chỉ có nhạc, (b) đoạn nói tại chỗ (walk & talk, ngồi kể), (c) đoạn "học" (hướng dẫn viên/bạn kể lịch sử, chèn bản đồ cổ và footage minh họa).
5. **Cuối:** nhịp chậm hẳn (1–9 cut/phút) với các đoạn nói dài 20–70s (suy ngẫm, Q&A, giải thích), câu kết mở ("what's next? let's go find out"), end card "ELENA TABER / @ELENATABER" chữ sans giãn chữ trên cảnh thành phố.

**Hình ảnh**
- Rất nhiều drone và shot "người trong cảnh lớn" (nhân vật nhỏ giữa núi/đền). Quay bằng máy ảnh, có gimbal, ít selfie.
- Có người quay cho (shot nhân vật đi vào/ra khung, quay lưng, nhìn xa).
- Nhãn địa danh: chữ hoa sans đậm trắng giữa khung ("KALAN MOSQUE", "BUKHARA"), có lúc màu vàng ("ARUSHA"). Không có phụ đề chạy.
- Chuyển cảnh: chủ yếu hard cut theo beat; **light leak / film burn** cam ấm giữa các đoạn; **tay che lens / high-five vào camera** làm wipe; flash đen ngắn trước khi đổi chương.
- Màu: ấm, tương phản nhẹ, bầu trời giữ chi tiết, cảm giác film.

**Lời**: tiếng Anh, nói với camera như kể bạn nghe, có người bạn đồng hành cùng dẫn. Lời ngoài khung (voiceover) dùng khi kể lịch sử.

## 2. apinvy (hà vy): "nhật ký thân mật"

**Cấu trúc**
1. **0:00–0:18 cold open montage nhanh** (0.4–0.6s/shot): ăn, đi xe đạp, mua sắm, phố, đồ ăn, selfie ngạc nhiên. Title chữ **script + serif** kiểu tạp chí đứng yên suốt montage:
   - "Solo in Shanghai" chữ script trắng góc trái, "2026" nhỏ góc dưới trái, "@apinvy" góc dưới phải.
   - "Hà Nội" chữ script **vàng** giữa khung, ghép câu tiêu đề bằng sans nhỏ hai bên ("5 ngày ở … là **không** đủ", chữ nhấn in nghiêng vàng).
   - "Phú Quốc" tách hai chữ hai bên khung, chừa giữa cho nhân vật.
2. **Hành trình đến nơi:** máy bay (cửa sổ, cầm tờ giấy/áo, màn hình Spotify đang nghe), sân bay, app bản đồ, metro. Quay cận tay cầm điện thoại để giải thích cách đi.
3. **Nhận phòng/airbnb và nói chuyện dài trước camera** (10–20s mỗi cụm, có shot 50–150s không cắt): tự giới thiệu, giá phòng, cảm nhận thật, "fun fact". Cầm mic DJI hoặc Osmo Pocket.
4. **Thân video theo ngày/địa điểm:** ăn → mua sắm → cafe → đi dạo, mỗi chỗ là một cụm: shot thiết lập + nhãn địa chỉ nhỏ góc trên trái ("Cô Linh · 43C Lý Thường Kiệt, Hoàn Kiếm") → POV món ăn/món đồ → selfie phản ứng → nói nhận xét.
5. **Nhịp sóng:** phút montage 15–25 cut xen phút nói dài 0–5 cut. Không có cao trào, đi theo dòng thời gian.
6. **Kết:** không có end card. Cảnh đời thường cuối (dọn đồ, mèo, nói chuyện với bạn), nhạc lên, cắt đen.

**Hình ảnh**
- Gần như toàn bộ là selfie góc rộng cầm tay (iPhone / Osmo Pocket), POV tay cầm đồ, gương, quay đặt máy cố định khi ăn. Ít drone, ít cảnh lớn.
- Shot "hỏi đáp tại chỗ": quay vào bạn đi cùng trong xe, quán vỉa hè, giữ nguyên tiếng hiện trường.
- **Phụ đề nhỏ màu vàng/trắng** cho câu nói đùa, lời tự sự hoặc giải thích ("Maglev = tàu đệm từ"), *không* phụ đề toàn bộ. Text kiểu Instagram story ("Wander throuh the park") lâu lâu một lần. Nhãn địa điểm nhỏ có chấm màu ("• Pudong Airport").
- Cắt đen ngắn giữa các cụm (như Elena). Thỉnh thoảng có *jump cut* trong một đoạn nói dài để bỏ khoảng ngập ngừng.
- Màu: tự nhiên, sáng, trung thực theo iPhone, không grade nặng.

**Lời**: tiếng Việt, xưng tên ("Vy"), giọng chuyện trò, chèn "má ơi", "ê", review thẳng (giá tiền, ưu nhược). Gần như không voiceover sau. Nói tại chỗ là xương sống video.

## 3. So sánh nhanh

| | Elena | Vy |
|---|---|---|
| Nhịp | 17–27 cut/phút, đều | 9–14 cut/phút, sóng montage/nói dài |
| Mở | Montage điện ảnh + title tài liệu | Montage đời thường + title tạp chí script |
| Máy | Máy ảnh, drone, có người quay | Selfie góc rộng, POV, điện thoại |
| Chữ | Hoa, giãn, serif/sans tối giản | Script + serif + sans pha, vàng nhấn |
| Lời | Kể chuyện, có lớp lịch sử | Review thật, tán gẫu |
| Chuyển cảnh | Beat cut, light leak, tay che lens, whoosh-zoom, thẻ cuộn phim | Hard cut, flash đen, màn trập + chớp, whoosh, punch-in zoom |
| Nhạc | Đổi thể loại theo nơi đến, có lúc cinematic; tắt hẳn khi nói | Lo-fi/acoustic liên tục, chỉ hạ nhỏ khi nói |
| Kết | Suy ngẫm + end card tên kênh | Cảnh đời thường, cắt đen |

**Điểm chung (mẫu của thể loại):** cold open montage không lời 15–25s trước khi nói câu đầu tiên; title đặt chồng lên montage; nhãn địa danh trên màn hình thay cho phụ đề; flash đen ngắn khi đổi chương; nửa sau video nhịp chậm hơn nửa đầu.

## 4. Âm thanh (Gemini nghe, 25 đoạn × 8 phút)

Nguồn: `reference/youtube/<id>/gemini.json` và mục "Gemini" cuối mỗi `report.md`. Mốc thời gian lệch ±1–2s.
Tên SFX là Gemini đoán theo tai, chưa đo bằng công cụ.

### Elena Taber
- **Nhạc là động cơ của video.** Mỗi chương đổi một bài, mỗi bài một thể loại hợp với nơi đến: world-fusion
  electronic ở Uzbekistan, tribal/folk ở Tanzania, indie-folk acoustic khi đi bộ đường dài, synth u ám đoạn khó
  (sương mù, leo đêm), orchestral/cinematic khi lộ cảnh lớn, nhạc bản địa ở lễ hội. Cold open thường là bài có
  giọng hát "vocal swell" bay bổng.
- **Hạ nhạc mạnh khi nói, đẩy nhạc lên ở montage và chuyển cảnh.** Đoạn ngồi nói đầu video thường tắt nhạc hẳn.
- **Âm thanh hiện trường đặt dưới nhạc:** sỏi lạo xạo dưới giày, gió, suối, chuông bò, tiếng thở nặng khi leo,
  tiếng chợ. Mục đích là đưa người xem "vào" cảnh.
- **SFX ít nhưng có chủ đích:** tiếng **màn trập máy ảnh + chớp trắng** khi chạy chuỗi ảnh nhanh hoặc đổi chương;
  **whoosh-zoom** nối hai địa điểm; tiếng máy chiếu phim / film burn đi cùng **thẻ chương dạng cuộn phim 16mm**;
  tiếng nét vẽ khi bản đồ chạy đường đi.
- Kết video: chuyển sang beat lo-fi riêng cho outro.

### apinvy (hà vy)
- **Một lớp lo-fi / chill-hop / jazz / acoustic gần như liên tục**, đổi bài theo địa điểm hoặc buổi trong ngày
  (pop lo-fi ban đêm, acoustic ban ngày, jazz quán cafe sáng, piano nhẹ khi kết). Intro Thượng Hải mở bằng jazz
  vui rồi mới vào lo-fi.
- **Hạ nhạc khi nói nhưng vẫn nghe thấy**, khác Elena hay tắt hẳn. Có đoạn "storytime" dài tắt nhạc hoàn toàn,
  chỉ giữ tiếng quán, tiếng phố.
- **Tiếng hiện trường thật được giữ:** tiếng ăn, mở hộp, khoá kéo, chuông xe đạp, tiếng phố. Tiếng ăn có lúc
  được đẩy to lên.
- **SFX nhấn kiểu hài:** màn trập máy ảnh + chớp khi kết một cụm (bữa ăn, buổi mua sắm) hoặc chuyển buổi, như một
  "album ảnh"; whoosh khi đổi địa điểm, đi cùng nhãn địa điểm ở góc; chuông "ting" chuyển ngày; tiếng nuốt, chuông
  báo thức iPhone, "pop" khi mở hộp, tiếng reo khi khui đồ; **punch-in zoom** vào mặt hoặc đồ vật để gây cười.

### Hai kênh cùng làm
- Nhạc không lời là nền và hạ khi có tiếng nói. Montage không lời thì đẩy nhạc lên.
- Đổi bài nhạc là tín hiệu đổi chương / địa điểm.
- **Màn trập + chớp trắng** và **whoosh** là hai SFX chuyển cảnh chính. Không dùng meme hay SFX ồn ào.
- Giữ âm thanh hiện trường thật dưới nhạc.

### Chi tiết hình ảnh Gemini thấy thêm (đã đối chiếu frame khi ghi "✓")
- Elena: vòng tròn tiến độ % + độ cao "2,780 M / 9,120 FT" + nhãn trại vàng "MTI MKUBWA CAMP / DAY 2" (✓
  Kilimanjaro 7:39); tay che lens / high-five để mở và đóng đoạn nói (✓ 3:10); bản đồ động vẽ đường đi; nhãn tọa
  độ GPS; màn hình chia đôi (cảnh đẹp + selfie, hoàng hôn + ly rượu); thẻ chương kiểu cuộn phim.
- Vy: chia đôi màn hình khi thử đồ (✓ Phú Quốc 17:25); phụ đề nội tâm chữ nhỏ vàng nhạt trong ngoặc vuông "[ … ]"
  (✓ 22:55); khung tròn mở title Phú Quốc; screenshot Instagram chèn khi kể chuyện cũ; tag thương hiệu quần áo
  bằng @handle; dịch thuật ngữ trên màn hình ("Maglev = tàu đệm từ"); "flycam" giả bằng cách thổi vào lens rồi zoom ra.
