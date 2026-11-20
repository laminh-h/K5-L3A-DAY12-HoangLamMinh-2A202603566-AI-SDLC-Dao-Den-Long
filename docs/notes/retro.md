# Retro: Đảo Đèn Lồng (4 phase)

## 1. Tổng hợp đánh giá từng phase

| Phase | Kết quả | Có làm hỏng phase trước? | Cần chỉnh |
|---|---|---|---|
| 1: PRD-0, Contract v1.0 | Lõi headless đầy đủ, 34 test, 6 scenario. **Chưa có client 3D ở tag phase-1** | — | Đã ưu tiên Test Contract (chiếm 30 điểm) hơn đồ họa |
| 2: Ticket-02, v1.1 | Engine viết lại theo 12 bước xử lý bắt buộc, 3 bản đồ, Gió Lạc, Bùa Gió, tạm dừng. 72 test, 18 scenario, CI xanh | 11 test cũ đỏ, đều do luật bị thay → sửa kèm lý do `# T02` | Scenario "full night" thua sớm che mất kiểm tra hiệu năng → bắt buộc kiểm `end_ticks` |
| 3: Ticket-03, v1.2 | Dầu đèn tính bằng số nguyên 1/60, `drain`, thắng lúc bình minh, sức chứa tăng dần. ADR và CHANGELOG. 96 test, 25 scenario | 3 test cũ, đúng những chỗ ticket đánh dấu [THAY THẾ] | Kỳ vọng phải tính cả bước 2 (hao dầu trước khi châm) |
| 4: Ticket-04, v1.3 | Client 3D đầy đủ (bù phần GUI của P1–P3), bench, soak, bảng xếp hạng, dễ tiếp cận, đóng gói. 109 test | Không. Cờ `bench` của sim mặc định tắt | `p1_low_fps` sát ngưỡng trên GPU tích hợp |

## 2. Cái gì hiệu quả

- **Tách logic khỏi hiển thị ngay từ Phase 1.** Headless, soak, bench và client 3D dùng chung `sim.py`. Nhờ vậy client 3D làm muộn mà không phải sửa luật.
- **`game.contract.json` là nguồn số liệu duy nhất.** Khi Ticket-02 và Ticket-03 đổi số, chỉ cần sửa JSON và test.
- **Bộ đếm và dầu dùng số nguyên tick/FU.** Không có lỗi sai số số thực, và output tất định trên mọi máy.
- **Scenario chạy 2 lần và so từng byte**, nên tính tất định luôn được kiểm tra mà không phải nhớ.
- **Tối ưu dựa trên đo đạc:** dùng profile để tìm nút thắt (draw call, setter text) thay vì đoán. Kết quả đi từ 22.8 lên 111 fps.

## 3. Cái gì không hiệu quả

- Để client 3D tới Phase 4. Tag phase-1/2/3 thiếu phần "chơi được", dù headless đạt.
- Viết script vá dài bằng heredoc trong Bash bị lỗi phân tích 2 lần → chuyển sang ghi script vào file rồi chạy.
- Một số ước tính "chắc là đúng" mà không đo. Ví dụ: số đo bench lúc cửa sổ bị thu nhỏ (8.5 fps) suýt bị commit làm `bench.json`.

## 4. Những lần AI sai và cách phát hiện

| # | Lỗi | Phát hiện bằng | Chỉnh harness |
|---|---|---|---|
| 1–8 | **Kỳ vọng sai trong test hoặc scenario** (8 lần): quên Bóng Mực di chuyển ở bước 8 trước khi chạm ở bước 9; quên hao dầu ở bước 2; cho rằng thả nút pause là tiếp tục; tính sai tick đầu của `drain`… | Test đỏ, rồi **tính tay lại theo thứ tự tick**. Không lần nào sửa engine cho khớp với test sai | AGENTS.md: "trước khi đổ lỗi cho engine, tính lại kỳ vọng theo thứ tự bước" |
| 9 | Bug thật: runner dừng khi `paused` | Test pause | — |
| 10 | Bằng chứng yếu: scenario hiệu năng PASS dù game thua ở tick 1140 | Thời gian chạy 0.2 s thấy vô lý | Skill `verify-phase` bước 6, quy tắc trong AGENTS.md |
| 11 | Bug hiển thị: thanh dầu dùng đơn vị nội bộ (6000) chứ không phải 100, nên vạch cam chạy ngang màn hình | **Đọc ảnh chụp màn hình** | Quy tắc "fuel là FU" trong AGENTS.md |
| 12 | Thuộc tính `right` của HUD trùng property của `Entity` trong Ursina | Traceback | Dùng namespace riêng cho HUD |
| 13 | Font thiếu glyph (● ⚠ 🍃) | Ảnh chụp có ô vuông | Thay bằng hình hoặc `(!)` |

## 5. Harness giúp nhiều nhất

1. **Stop hook** (`.claude/hooks/stop_check.py`): không cho agent kết thúc khi test hoặc scenario đỏ. Nó chặn việc "agent bảo xong" khi chưa xanh.
2. **`tools/run_scenarios.py`**: một lệnh vừa sinh bằng chứng, vừa kiểm tất định, vừa ra bảng truy vết.
3. **AGENTS.md** ngắn (khoảng 30 dòng), cập nhật mỗi phase với các lỗi AI đã mắc. Lịch sử git thể hiện được điều này.
4. **Chế độ `--screenshot` / `--ui` / `--overview`**: cho agent "nhìn" game. Lỗi 11 và 13 chỉ phát hiện được nhờ ảnh.

## 6. Token và chi phí

**Số đo thật** (lệnh `/usage` của Claude Code, gói Claude Pro, ngày 2026-11-20). Gói Pro **không hiển thị số token hay chi phí tuyệt đối**, chỉ có phần trăm hạn mức:

| Chỉ số | Giá trị |
|---|---|
| Hạn mức phiên 5 giờ đã dùng (cả buổi lab: 4 phase + video) | **76%** |
| Hạn mức tuần đã dùng | **11%** |
| Đóng góp lớn nhất vào hạn mức (theo `/usage`) | **91%: "Start fresh when you switch tasks"** (không `/clear` khi đổi việc) |
| Đóng góp khác | 12% "See what fills your context", 11% "Ask Read for less" (đọc file lớn, tới ~28k token × 2 lần) |
| Model | Claude Opus 5.5, effort Medium, không dùng subagent |

**Số token thật** (cộng trường `usage` trong log hội thoại Claude Code lưu trên máy, 137 lần gọi `claude-opus-5-5`):

| Loại | Token |
|---|---|
| Đầu ra (output) | 308.807 |
| Ghi cache (cache creation) | 435.743 |
| Đọc cache (gửi lại ngữ cảnh mỗi lượt) | 41.876.650 |
| Đầu vào không cache | 304 |
| **Tổng** | **≈ 42,6 triệu** |

Khoảng **98% là đọc lại ngữ cảnh**; phần AI thực sự sinh ra chỉ khoảng 0,3 triệu token. Điều này khớp với `/usage` (91% do không `/clear`). Chi phí tiền: nằm trong thuê bao Pro, không tính theo token.

**Phân tích:** chi phí chủ yếu không nằm ở việc sinh code mà ở **ngữ cảnh tích lũy**. Mình giữ một hội thoại duy nhất xuyên suốt 4 phase, nên mỗi lượt phải gửi lại toàn bộ lịch sử. Cách tiết kiệm lớn nhất bị bỏ lỡ là `/clear` hoặc mở phiên mới ở đầu mỗi phase, sau khi AGENTS.md và tài liệu spec đã đủ để agent nắm lại bối cảnh.

| Phase | Ước tính tương đối* | Đã tiết kiệm bằng cách |
|---|---|---|
| 1 | thấp | stdlib, không cài gói; đọc tài liệu một lần |
| 2 | cao (engine + 38 test) | Viết engine một lần theo đúng thứ tự bước, sinh scenario bằng script |
| 3 | trung bình | Vá đúng chỗ bằng script, tái dùng helper của test |
| 4 | cao nhất (client 3D, tối ưu, video) | Profile trước khi tối ưu; chụp ảnh để kiểm tra thay vì đoán |

\* Không đo được theo từng phase (gói Pro chỉ hiện tổng phần trăm). Mức tương đối ước lượng theo khối lượng công việc và độ dài ngữ cảnh lúc đó.

## 7. Nếu làm lại

- **`/clear` hoặc mở phiên mới ở đầu mỗi phase** (theo `/usage`, đây là nguồn tiêu hao chiếm 91%). AGENTS.md và spec trong `docs/notes/` đã đủ để agent nắm lại bối cảnh.

- Làm **một client 3D tối giản ngay trong Phase 1** (khoảng 30 phút), rồi mới mở rộng.
- Thêm một script "playtest" quay video tự động từ sớm, để có bằng chứng hình ảnh mỗi phase.
- Đặt ngân sách hiệu năng (draw call) ngay khi dựng client, thay vì tối ưu ở cuối.
