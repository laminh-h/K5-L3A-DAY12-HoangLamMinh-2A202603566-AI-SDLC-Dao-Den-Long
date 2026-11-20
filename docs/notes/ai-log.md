# Nhật ký dùng AI

Công cụ: Claude Code (VS Code extension), model Claude Opus 5.5.

## Phase 1

| Bước | Việc giao cho AI | Kết quả / chỗ AI sai | Cách phát hiện |
|---|---|---|---|
| 1 | Đọc 6 file tài liệu lab, tóm tắt yêu cầu | Đúng | Tự đối chiếu với README |
| 2 | Đọc lab board | Chỉ thấy tab Phase 1; tab Phase 2 chưa phát hành | — |
| 3 | Chọn stack | Máy không có Node/Docker nên chọn Python stdlib cho headless, Ursina cho 3D | Kiểm tra `node --version` |
| 4 | Viết `sim.py`, `headless.py`, `contract_io.py` | Chạy được ngay, 2 lần chạy cho output giống hệt | So file bằng `cmp` |
| 5 | Viết 34 unit test | **AI viết sai test**: `test_spawned_shades_emit_events` cho người chơi đứng yên giữa 2 Bóng Mực, nên người chơi thua trước giây 30. Đã sửa test (bắt đầu với 0 Bóng Mực), không sửa game | Test đỏ, đọc lại kịch bản |
| 6 | Viết scenario 02 | **AI tính sai kỳ vọng**: 400 tick đủ cho 2 lần chạm. Tính tay lại: hết choáng ở tick 181, đi 6 m với 4 m/s mất 90 tick, chạm ở tick 271 (khớp output). Đổi thành 300 tick | Script báo FAIL, tính tay |

Bài học → harness: thêm vào AGENTS.md và skill `verify-phase` quy tắc *"kỳ vọng phải tính từ yêu cầu và tuning, không chép output"*, cùng Stop hook chặn kết thúc khi test đỏ.

## Phase 2

| Bước | Việc giao cho AI | Kết quả / chỗ AI sai | Cách phát hiện |
|---|---|---|---|
| 1 | Viết lại engine theo 12 bước bắt buộc, `maps.py`, contract v1.1 | 11 test cũ đỏ, **tất cả** do luật cũ bị thay (không có lỗi engine) → sửa test, đánh dấu `# T02`, ghi lý do | Đọc từng lỗi, đối chiếu với ticket |
| 2 | Viết 38 test mới | **AI sai 3 kỳ vọng**: (a) cho rằng thả nút pause là tiếp tục game; (b) quên bước 8 (Bóng Mực di chuyển) diễn ra trước bước 9 (chạm); (c) so tọa độ đã làm tròn với sai số 1e-3 | Tính tay lại theo thứ tự tick |
| 3 | Runner headless | **Bug thật**: dừng khi `state != "playing"` nên dừng luôn khi `paused` | Test pause |
| 4 | Scenario "full night" | **AI đưa bằng chứng yếu**: scenario thua sớm (tick 1140–2018) nhưng vẫn PASS, nên không chứng minh được ≤ 30 s | Thời gian 0.2 s thấy vô lý → xem dòng `end` |

Harness được cập nhật: AGENTS.md thêm 3 quy tắc (thứ tự bước, scenario full night phải kiểm `end_ticks`, đánh dấu test bị ticket thay); Stop hook và CI chạy scenario phase-2.

### Token / chi phí (ước tính)

| Phase | Ước tính | Cách tiết kiệm |
|---|---|---|
| 1 (lõi + headless + test + harness) | ~cập nhật sau khi xem `/cost` | Đọc tài liệu một lần; dùng stdlib (không cài gói); test và scenario chạy local, không lặp agent |
| 2 (engine v1.1, 3 bản đồ, 38 test mới, 12 scenario) | ~cập nhật sau khi xem `/cost` | Viết engine một lần theo đúng thứ tự bước thay vì vá dần; sinh scenario bằng script; không chạy subagent |
