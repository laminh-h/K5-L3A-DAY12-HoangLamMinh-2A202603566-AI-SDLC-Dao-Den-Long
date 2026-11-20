# Bằng chứng Phase 4 (Contract v1.3, Ticket-04)

Máy đo: laptop Windows 10, Intel UHD Graphics 620 (GPU tích hợp), Python 3.13.1, Ursina 7.0.0 / Panda3D 1.10.16. Số đo chính thức là của máy chấm; số dưới đây chỉ để tham khảo.

## 1. Benchmark: [bench.json](../../../bench.json)

`.venv/bin/python -m lantern.app --bench --seed 42 --duration 30 --out bench.json`

| Lần chạy | avg_fps (≥ 60) | p1_low_fps (≥ 30) | frame_ms_p95 | load_ms (≤ 10000) | peak_mem_mb | Ghi chú |
|---|---|---|---|---|---|---|
| **bench.json (chính thức)** | **104.7** | **35.4** | 15.65 | **1905** | 147.8 | Đạt |
| [bench_run1.json](bench_run1.json) | 120.3 | 38.3 | 12.48 | 1803 | 148.6 | Đạt |
| [bench_run2.json](bench_run2.json) | 102.8 | **26.6** | 15.5 | 1568 | 153.5 | **p1_low chưa đạt**; cửa sổ bị thu nhỏ 2 khung |

**Nhận xét trung thực:** trên GPU tích hợp này, `p1_low_fps` dao động quanh ngưỡng 30, vì máy đang chạy cùng VS Code. `avg_fps` và `load_ms` luôn đạt với khoảng dư lớn.

Cảnh bench theo đúng Ticket-04:
- 200 Bóng Mực ở trạng thái `wander`, 100 đom đóm, L1–L3 sáng với fuel 100;
- tắt sinh thêm, sát thương, nhặt, hao dầu và điều kiện kết thúc;
- camera bay tròn bán kính 30 m ở Y = 15, 15 s một vòng ngược chiều kim đồng hồ;
- 3 s khởi động rồi đo 30 s.

Phần logic của cảnh có test trong `tests/test_phase4.py::BenchScene`, gồm cả công thức `avg_fps`, `p1_low_fps`, P95. Ảnh cảnh bench: [bench.png](../../img/bench.png).

### Quá trình tối ưu (đo thật, cùng cảnh)

| Bước | avg_fps | p1_low_fps |
|---|---|---|
| Bản đầu: mỗi Bóng Mực 3 Entity, mỗi đom đóm 2 Entity, setter Ursina mỗi khung | 22.8 | 12.8 |
| Gộp mesh bằng màu đỉnh (1 node/vật), `setPos` trực tiếp, `flattenStrong` bản đồ tĩnh | 64.2 | 22.9 |
| HUD chỉ gán text/màu khi đổi, `gc.freeze()` sau khi tải | 83.8 | 27.2 |
| `RigidBodyCombiner` cho Bóng Mực và đom đóm (vài draw call cho 300 vật) | 111.2 | 40.3 |

Phát hiện thêm: Panda3D `ShowBase` ngủ 0.1 s mỗi khung khi cửa sổ bị thu nhỏ (một lần đo ra 8.5 fps). Bench giờ giữ cửa sổ ở trạng thái mở và báo số khung bị thu nhỏ trong `minimized_frames`.

## 2. Soak: [soak.json](../../../soak.json)

`.venv/bin/python -m lantern.soak --seed 7 --nights 10 --out soak.json` cho `crashes: 0`, `mem_start_mb 15.7`, `mem_end_mb 15.7` (≤ 1.2×): **Đạt**.

Ghi chú: input ngẫu nhiên theo spec (đổi hướng mỗi 30 tick, 5% nhảy, 3% lướt…) khiến Mây thường rơi khỏi đảo, nên cả 10 Đêm đều thua sớm (tổng 2.4 s). Đây đúng là hành vi của luật. Test `Soak` trong `tests/test_phase4.py` kiểm tra không crash và kết quả tất định.

## 3. Bảng xếp hạng

| Tiêu chí | Bằng chứng | Kết quả |
|---|---|---|
| Tên 3–12 ký tự `[A-Za-z0-9_]`, có hỗ trợ tiếng Việt có dấu (điểm cộng) | `test_name_rules` | Đạt |
| Lưu name, score, nights_won, achieved_at (ISO 8601 có múi giờ), seed; giữ top 10; điểm giảm dần, bằng điểm thì ai đạt trước đứng trên | `test_top10_sort_and_tie_order` | Đạt |
| Lưu trên đĩa (`~/.dao_den_long/leaderboard.json`), còn sau khi mở lại | `test_persist_and_export_cli` | Đạt |
| `run_cmd --export-leaderboard out.json` | `test_persist_and_export_cli` (gọi CLI thật) | Đạt |
| Nhập tên sau Bình Minh hoặc sau khi thua; màn hình Bảng xếp hạng từ menu | [ui_name.png](../../img/ui_name.png), [ui_leaderboard.png](../../img/ui_leaderboard.png) | Đạt |

## 4. Dễ tiếp cận

| Tiêu chí | Bằng chứng | Kết quả |
|---|---|---|
| Đổi phím cho cả 9 hành động, báo phím trùng, khôi phục mặc định, có lưu | `Settings` tests, [ui_keys_conflict.png](../../img/ui_keys_conflict.png) | Đạt |
| Phụ đề: Bóng Mực xuất hiện kèm mũi tên ở mép màn hình, gió sắp thổi, 10 s cuối, đèn có fuel < 30 | [night1.png](../../img/night1.png), [night3.png](../../img/night3.png); code `update_hud` | Đạt (kiểm bằng ảnh và đọc code) |
| Giảm chuyển động: tắt rung camera, chớp màn hình, nháy đồng hồ | `reduced_motion` trong `handle_events` / `update_hud` | Đạt (đọc code) |
| Chữ ≥ 18 px ở 720p, tùy chọn ×1.25 | `ui_text`: scale ≥ 1 (0.025 × 720 = 18 px); [ui_settings.png](../../img/ui_settings.png) | Đạt |
| Chế độ mù màu (Ticket-03): viền và mắt #00B3FF, cảnh báo trắng kèm (!), đèn tắt bị xẹp và rách | [night3.png](../../img/night3.png) (mũi tên xanh), [ui_keys_conflict.png](../../img/ui_keys_conflict.png) | Đạt |

## 5. Hoàn thiện các mục GUI còn thiếu của Phase 1–3

| Mục | Bằng chứng |
|---|---|
| P1: Đêm 1 chơi được, HUD, chơi lại | [night1.png](../../img/night1.png), [ui_pause.png](../../img/ui_pause.png) (Chơi lại Đêm) |
| P2: menu, giới thiệu Đêm (Ông Đăng), chuỗi 3 Đêm, Bình Minh, tạm dừng, cài đặt có lưu, âm thanh (13 file tự sinh), HUD đầy đủ, bảng màu chuẩn, ánh sáng tăng theo số đèn | [ui_menu.png](../../img/ui_menu.png), [night2.png](../../img/night2.png), [overview3.png](../../img/overview3.png) |
| P2: ≥ 30 FPS ở 1280×720 | Bench ≥ 100 avg_fps với 200 Bóng Mực |
| P3: thanh dầu, nhấp nháy 1 Hz khi < 30, chế độ mù màu | `World._upd_lantern` |

**Giới hạn của bằng chứng:** các ảnh trên do bot `--autoplay` / `--screenshot` của game chụp. Tác giả cần **chơi thử bằng bàn phím và chuột** và quay video demo, vì phần này AI không tự làm được.

## 6. Regression

`python3 -m unittest discover -s tests -t .` cho 109 test đạt. `python3 tools/run_scenarios.py --phase phase-4` cho 25/25 scenario đạt ([scenarios.md](scenarios.md)). Cờ `bench` của sim mặc định tắt, nên output headless của v1.0–v1.2 không đổi.
