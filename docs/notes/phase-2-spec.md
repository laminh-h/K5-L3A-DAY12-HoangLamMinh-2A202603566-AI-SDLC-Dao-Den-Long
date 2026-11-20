# Phase 2 (Ticket-02, Contract v1.1): spec, giả định, tiêu chí nghiệm thu

## 1. Thay đổi so với Phase 1

- **Số liệu chuẩn thay toàn bộ số tự chọn.** `game.contract.json` lên v1.1. Số chuẩn không phải khóa tuning nằm trong `lantern/config.py`.
- **Bản đồ chuẩn** của 3 Đêm nằm trong `lantern/maps.py`. Góc đo từ +X về phía +Z: `(r cos a, r sin a)`. Cách đo này kiểm chứng được qua yêu cầu "tầng 1 ở nửa z > 0" với các góc 20°…160°.
- **Engine viết lại theo đúng 12 bước bắt buộc** của Ticket-02 (`lantern/sim.py`, docstring đầu file).

## 2. Giả định cho chỗ Ticket-02 chưa quy định

| # | Chỗ mơ hồ | Giả định |
|---|---|---|
| B1 | Tăng tốc/dừng ≤ 0.1 s | Vận tốc đổi tức thời (0 s ≤ 0.1 s) |
| B2 | Trạng thái `spawning` | Kéo dài 60 tick, đứng yên, không gây sát thương |
| B3 | `wander` | Đi 2 m/s về đèn **chưa sáng** gần nhất, dừng khi cách 2 m (Ticket-03 xác nhận "đi về đèn tắt gần nhất") |
| B4 | Hết choáng hoặc hết recoil | Về `wander`, rồi chuyển `chase` nếu Mây trong 12 m |
| B5 | Bóng Mực bị đẩy ra khi đèn vừa thắp | Hiện `state: "recoil"` trong lúc bị đẩy (tối đa 30 tick, vô hại). Nếu đang `stunned` thì giữ `stunned` |
| B6 | Độ cao Bóng Mực | Bám mặt đất `ground(x,z)`. Trên biển mây thì giữ độ cao cũ |
| B7 | Tháp chuông, vật cản | Trụ r = 2 m chặn Mây (khi Y < 14) và chặn đẩy lùi Bóng Mực |
| B8 | Tường và dốc | Bậc ≤ 0.35 m mỗi tick thì đi được (dốc). Cao hơn là tường. Thử trượt theo từng trục X/Z |
| B9 | **Xuất phát Đêm 3** | **(0,0,−30)** vì (0,0,0) nằm trong khối tầng 2 / tháp chuông. Đêm 1, 2: (0,0,0) |
| B10 | Điểm sinh Gió Lạc | Chọn ngẫu nhiên trong các điểm sinh Bóng Mực. `idle` lượn 2 m/s tới waypoint ngẫu nhiên. Bay cao 1 m trên mặt đất |
| B11 | Tỏa Sáng trúng Gió Lạc | Cùng luật khoảng cách 3D ≤ 5 m. Trúng con `idle` thì không có gì xảy ra. Gió Lạc không nằm trong `stunned_ids` và không cộng điểm |
| B12 | Gió Lạc bị xóa | Xóa khỏi mảng `drifters` (không giữ phần tử `removed`) |
| B13 | Trần 30 đom đóm | Tính mọi đom đóm đang có (random + dropped). "Điểm trống" là điểm sinh không có đom đóm random nào đứng |
| B14 | `night_start` | Ghi ở tick 0, là **dòng đầu tiên**, trước snapshot tick 0 |
| B15 | Gió mạnh | Bắt đầu ở sim_tick 1800, 3600, … (mỗi 30 s), kéo dài 300 tick, hướng `rng.uniform(0,360)`. `wind_enabled` mặc định bật ở Đêm 3 |
| B16 | Snapshot `invuln`, `*_cd_s`, `charm_s` | Số giây còn lại. `wind.dir_deg = null` khi không có gió |
| B17 | Hồi sinh sau khi rơi | Rơi ở tick f, hồi sinh ở tick f+60. Trong lúc chờ không di chuyển, không nhặt, không bị chạm, không tương tác, không pulse |
| B18 | Bục nhảy | Kích hoạt khi chạm đất trong XZ ≤ 1 m tâm bục. Vận tốc phóng bắt đầu từ tick sau |
| B19 | Tạm dừng | Mỗi lần nút pause chuyển false→true thì bật/tắt. Thả nút **không** tiếp tục game |

## 3. Tiêu chí nghiệm thu (Phần 3 và các luật chính)

| ID | Tính năng | Tiêu chí kiểm được | Test / scenario |
|---|---|---|---|
| P2-1 | Số chuẩn: chạy, nhảy | 60 tick đi 6.0 m. Nhảy cao ≈ 1.225 m, ở trên không ≈ 0.7 s, không nhảy kép | `Movement`, `tests/test_rules.py` |
| P2-2 | Lướt | 12 tick × 14 m/s = 2.8 m. Hồi chiêu 90 tick tính từ lúc bắt đầu. Đứng yên thì lướt theo hướng mặt. Lướt trên không giữ độ cao | `Dash`, scenario 07 |
| P2-3 | Đom đóm | 20 ở 20 điểm khác nhau. +1 ở tick 240, 480… Nhặt khi XZ ≤ 1 và chênh cao ≤ 1.5 | `Motes` |
| P2-4 | Đèn | Bán kính 2 m, nhớ tiến độ, bằng nhau thì chọn id nhỏ hơn. +10 mỗi đom đóm nạp, +100 mỗi đèn | `Lanterns` |
| P2-5 | Vùng an toàn 6 m | Bóng Mực bị chặn ở mép. Con bên trong lúc đèn vừa thắp bị đẩy ra trong ≤ 30 tick, không gây sát thương | `SafeZone` |
| P2-6 | Tỏa Sáng | Chi phí 3, bán kính 5 m (3D từ chân + 0.8), hồi 180 tick, choáng 120 tick, đẩy 4 m trong 15 tick, +5 mỗi con (kể cả con đang choáng) | `Pulse`, scenario 02 |
| P2-7 | Bóng Mực | Phát hiện 12 m, bỏ đuổi 18 m. Chạm: −1 lửa, rơi floor(n/2) đom đóm ra vành 1.5–2.5 m (TTL 480), bất tử 90 tick, recoil 2 m / 60 tick. Mỗi tick tối đa 1 hit, xét id tăng dần | `Shades` |
| P2-8 | Lịch sinh Bóng Mực | Tick 300: S1, S2. Sau đó +1 mỗi 480/420/360 tick, tối đa 6/8/10, cách người chơi ≥ 15 m. Tốc độ Đêm 3 là 4.5 m/s | `test_spawn_*`, `test_shade_speed_45`, scenario 15 |
| P2-9 | Rơi khỏi đảo | Y < −10: −1 lửa, mất toàn bộ đom đóm (`lost`), chờ 60 tick, hồi sinh, bất tử 1.5 s. Lửa cuối thì thua | `Fall`, scenario 08 |
| P2-10 | Đêm 2 | 6 đèn, cầu tre đi được, ra mép cầu thì rơi. Bục nhảy đáp đảo kia sau ≈ 1.4 s | `Night2Map`, scenario 09 |
| P2-11 | Đêm 3 | Tường tầng 1, dốc lên Y = 3, bục nhảy lên tầng 2 (Y = 6), gió 2 m/s mỗi 30 s trong 5 s | `Night3Map`, scenario 10, 16 |
| P2-12 | Gió Lạc | Đuổi khi mang ≥ 5 và cách ≤ 15 m. Cướp min(3, n), bỏ chạy 240 tick rồi biến mất. Pulse lúc chase → flee. Pulse lúc flee có đồ → thả lại, biến mất sau 120 tick. Vùng an toàn và bất tử không ngăn được. Sinh ở tick 1200, 2400 (D1, D2) | `Drifters`, scenario 11, 12 |
| P2-13 | Bùa Gió | Nhặt → 600 tick, chạy 7.2 m/s, lướt không hồi chiêu, hồi lại sau 2700 tick. Đêm 2: C1 ở (35,0,0) | `Charm`, scenario 13 |
| P2-14 | Tạm dừng | `tick` tăng, `sim_tick`/thời gian/vị trí đứng yên, `state: "paused"`, có sự kiện `paused`/`resumed` | `Pause`, scenario 14 |
| P2-15 | Thắng/thua | Thứ tự xét: hết lửa → `no_flames`. Còn sống và đủ đèn → thắng (kể cả đúng tick hết giờ). Còn lại hết giờ → `dawn`. Thưởng: floor(giây) × 2 + 50 × lửa | `test_win_*`, scenario 03–05 |
| P2-16 | Contract v1.1 | `--night 1..3`, các trường snapshot và scenario mới, sự kiện mới, tên trạng thái chuẩn | `test_snapshot_v11_fields`, `test_cli.py` |
| P2-17 | Hiệu năng headless | Một Đêm đầy đủ 21.600 tick ≤ 30 s | `Performance`, scenario 17, 18 (~2 s) |
| P2-18 | Chuỗi 3 Đêm, menu, cài đặt, âm thanh, HUD, bảng màu, ≥ 30 FPS | Kiểm tra trên bản 3D | **Chưa đạt**: chưa có client 3D (ưu tiên headless) |

## 4. Test bị Ticket-02 làm sai: đã sửa, không xóa

| Test | Lý do sửa |
|---|---|
| `test_pickup_radius_inclusive` | Điểm giờ cộng khi **nạp** (+10 mỗi đom đóm), nhặt không còn được điểm |
| `test_deposit_and_light`, `test_win_all_lit_and_bonus` | Điểm mới: 10 × 10 + 100 và thưởng giây × 2 |
| `test_pulse_*` | Chi phí 3, bán kính 5 m (3D), đẩy lùi trong 15 tick, hồi chiêu 3 s, choáng 2 s, +5 |
| `test_shade_chases_at_speed` | Phát hiện 12 m nên vị trí đầu đổi từ 20 m thành 10 m. Thêm `test_far_shade_wanders` |
| `test_spawned_shades_emit_events` | Thay bằng `test_spawn_schedule_night1` (tick 300, sau đó mỗi 480) |
| `test_scenario_lit_gives_no_score`, `test_ok_run_and_jsonl`, `test_contract_file` | Dòng đầu tiên giờ là `night_start`; contract lên 1.1 |
| Scenario 01–05 | Thêm `night_start` vào đầu danh sách sự kiện. Scenario 01: điểm 120 → 200 |
