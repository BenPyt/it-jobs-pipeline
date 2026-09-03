# IT Jobs Pipeline — thu thập, làm sạch & trực quan hoá tin tuyển dụng IT Việt Nam

Pipeline dữ liệu end-to-end: **crawl → làm sạch → lưu SQLite → dashboard Streamlit**.
Dữ liệu lấy từ các trang tuyển dụng IT (ITviec, TopCV) để trả lời những câu hỏi thực tế:
kỹ năng nào đang được tuyển nhiều nhất, mức lương theo cấp bậc ra sao, thị trường tập trung ở đâu.

## Kiến trúc

```
              ┌──────────────┐      ┌───────────────┐      ┌──────────────┐
  Web  ─────► │  src/crawl   │ ───► │   src/clean   │ ───► │  src/store   │ ──► SQLite
              │  (scraper)   │ raw  │ (chuẩn hoá)   │ tidy │  (upsert)    │
              └──────────────┘ JSON └───────────────┘  CSV └──────────────┘
                                                                  │
                                                                  ▼
                                                        dashboard/app.py (Streamlit)
```

| Thư mục | Vai trò |
|---|---|
| `src/crawl/` | Scraper theo từng nguồn (`itviec.py`, `topcv.py`) + HTTP client có retry & rate limit |
| `src/clean/` | Chuẩn hoá lương, địa điểm, kỹ năng, cấp bậc; khử & gộp trùng lặp |
| `src/store/` | Lược đồ SQLite + ghi dữ liệu idempotent |
| `dashboard/` | Ứng dụng Streamlit |
| `data/raw/` | Dữ liệu thô theo từng lần chạy (JSONL + snapshot HTML kèm `_index.jsonl`) |
| `data/processed/` | CSV đã làm sạch |
| `tests/` | Test cho parser HTML, parser lương, và luồng end-to-end |

## Cài đặt

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
```

## Chạy

```bash
# 1) Chạy pipeline thật (crawl → làm sạch → ghi CSDL)
python run_pipeline.py

# Vài biến thể hữu ích
python run_pipeline.py --sources itviec --max-pages 2 --no-detail
python run_pipeline.py --from-raw data/raw/jobs_20260903_120000.jsonl  # làm sạch lại, không crawl
python run_pipeline.py --from-html data/raw/html_20260903_142919      # bóc tách lại từ HTML đã lưu

# 2) Mở dashboard
streamlit run dashboard/app.py
```

Chưa muốn crawl mà vẫn xem thử dashboard:

```bash
python scripts/make_sample_raw.py
python run_pipeline.py --from-raw data/raw/SAMPLE_jobs_demo.json
```

> ⚠️ Dữ liệu do `make_sample_raw.py` sinh ra là **mô phỏng**, chỉ để kiểm thử giao diện.
> Dashboard sẽ hiện cảnh báo đỏ khi phát hiện dữ liệu này trong CSDL.

## Những quyết định kỹ thuật đáng chú ý

**1. Parser không bám vào tên class CSS.**
Class trên trang tuyển dụng đổi liên tục và crawler sẽ chết âm thầm. Ở đây neo vào thứ bền hơn:
dạng URL của tin (`/it-jobs/<slug>-<id>`, `/viec-lam/<slug>/<id>.html`) và quan hệ cha–con
(card = tổ tiên gần nhất chứa cả link tin lẫn link công ty). Tên class chỉ dùng làm gợi ý ưu tiên,
luôn có đường lui bằng regex trên văn bản.

**2. Lương là bài toán chính của khâu làm sạch.**
Cùng một khái niệm nhưng dữ liệu thật viết đủ kiểu: `Thoả thuận`, `Sign in to view salary`,
`$1,000 - $2,000`, `Tới 1,500 USD`, `10 - 20 triệu`, `Trên 20 triệu`, `20.000.000 VND`.
`src/clean/salary.py` quy tất cả về `(min, max, currency, disclosed)` theo VND, và phân biệt rõ
**không công bố** với **bằng 0** — mọi thống kê lương chỉ tính trên phần có công bố.

**3. Trùng lặp giữa các nguồn thì gộp, không vứt.**
Một tin đăng cả trên ITviec lẫn TopCV: ITviec ẩn lương nhưng gắn tag kỹ năng chuẩn,
TopCV công bố lương. Vứt một bản là mất dữ liệu, nên `_merge_group` giữ bản đầy đủ nhất
rồi bù các ô trống và hợp nhất danh sách kỹ năng từ các bản còn lại.

**4. Tầng raw ghi theo dòng (JSONL), không gom vào RAM.**
Mỗi tin được ghi xuống đĩa ngay khi lấy được, mỗi dòng một object JSON độc lập.
Crawler chết ở tin thứ 900 thì 899 tin trước vẫn còn nguyên — với file JSON thường
(phải kết thúc bằng `]`) thì file cụt là file hỏng, mất sạch. Kèm theo đó, mỗi trang
HTML tải về được ghi lại cùng một sổ mục `_index.jsonl` (URL nào ứng với file nào),
nên `--from-html` có thể bóc tách lại toàn bộ mà không cần chạm vào mạng.

**5. Ghi CSDL idempotent.**
Chạy pipeline 10 lần trên cùng dữ liệu thì CSDL vẫn chỉ có một bản ghi mỗi tin, chỉ cập nhật
`last_seen_at`. Nhờ vậy có thể chạy lại bất cứ lúc nào, và cặp `first_seen_at` / `last_seen_at`
cho biết tin còn sống hay đã bị gỡ.

**6. Bẫy Unicode tiếng Việt.**
`unicodedata.normalize("NFD", ...)` **không** tách được dấu của chữ `Đ`/`đ` (đây là ký tự riêng,
không phải `D` + dấu). Không xử lý riêng thì "Đà Nẵng" sẽ không bao giờ khớp với "da nang" và
toàn bộ tin ở Đà Nẵng bị mất khỏi thống kê.

## Test

```bash
pytest -q
```

Test chạy hoàn toàn offline bằng fixture HTML trong `tests/fixtures/`, gồm: bóc tách HTML,
chuẩn hoá lương, gộp trùng giữa hai nguồn, và tính idempotent của tầng lưu trữ.

## Lưu ý khi crawl

- Chỉ crawl trang danh sách công khai, có nghỉ giữa các request (`crawl.http.delay_seconds`)
  và User-Agent trung thực; không đăng nhập, không vượt tường phân quyền.
- Tôn trọng `robots.txt` và điều khoản sử dụng của từng trang. Dữ liệu thu thập dùng cho mục đích
  học tập / phân tích cá nhân.
- Selector có thể lỗi thời khi trang đổi giao diện — snapshot HTML trong `data/raw/html_*/`
  cho phép kiểm tra lại và sửa parser mà không phải crawl lại từ đầu.

## Hướng phát triển tiếp

- Thêm nguồn (VietnamWorks, LinkedIn Jobs) — chỉ cần thêm một file trong `src/crawl/` và đăng ký vào `SCRAPERS`.
- Theo dõi theo thời gian: chạy định kỳ để vẽ xu hướng nhu cầu kỹ năng theo tuần/tháng.
- Trích kỹ năng từ phần mô tả công việc bằng NLP thay vì chỉ dựa vào tag có sẵn.
- Dự đoán khoảng lương cho các tin ghi "Thoả thuận" từ tiêu đề + kỹ năng + công ty.
