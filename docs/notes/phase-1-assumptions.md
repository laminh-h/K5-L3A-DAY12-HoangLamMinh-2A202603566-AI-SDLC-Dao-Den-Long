# Phase 1: giả định và tiêu chí nghiệm thu

Nguồn: PRD-0 và Test Contract v1.0 (lab board, tab Phase 1).

## 1. Quyết định kiến trúc

| Quyết định | Lý do |
|---|---|
| Python 3, chỉ dùng stdlib cho logic và headless | Máy dev không có Node/Docker. `python3` có sẵn trên macOS/Linux nên headless chạy được mà không cần cài gì |
| `lantern/sim.py` tách hẳn khỏi phần 3D (`lantern/app.py`, Ursina) | Contract yêu cầu chạy không cần cửa sổ hay GPU. Game và test dùng chung một nguồn luật |
| Tuning đọc trực tiếp từ `game.contract.json` | Số khai báo luôn khớp số game dùng, vì khai sai là trượt test ẩn |
| Bộ đếm thời gian tính bằng số tick nguyên (`round(s*60)`) | Tất định, tránh sai số float |

## 2. Giả định cho chỗ PRD-0 còn mơ hồ

| # | Chỗ mơ hồ | Giả định |
|---|---|---|
| A1 | "Máu" | Máu là `flames` = 3. Mỗi lần bị chạm mất 1 flame |
| A2 | Đom đóm bị rơi khi bị chạm | `dropped = floor(carried × hit_drop_ratio)`, ratio = 0.5. Đom đóm rơi **mất hẳn**, không rơi xuống đất |
| A3 | Sau khi bị chạm | Bất tử `invuln_s` = 1.5 s. Mỗi tick bị chạm tối đa 1 lần |
| A4 | "Nạp ánh sáng vào đèn" | Nhấn interact trong `interact_radius` = 2.5 m của đèn **chưa thắp** gần nhất. Nạp `min(carried, lantern_cost − deposited)`. Đèn sáng khi `deposited = lantern_cost` = 10. Được nạp nhiều lần |
| A5 | Tỏa sáng (pulse) | Tốn `pulse_cost` = 1 đom đóm đang mang, hồi chiêu 1 s. Không đủ đom đóm hoặc đang hồi chiêu thì không có gì xảy ra (không phát sự kiện). Mọi Bóng Mực trong 6 m bị choáng 3 s và bị đẩy ra xa thêm 4 m. Bóng Mực đang choáng vẫn bị choáng lại. Sự kiện `pulse` vẫn được ghi khi không trúng con nào (`stunned_ids: []`) |
| A6 | "Bóng Mực sợ đèn" | Chỉ **đèn đã thắp** có vùng an toàn `safe_radius` = 5 m. Bóng Mực bị giữ ở mép vùng (khoảng cách ≥ 5 m) |
| A7 | Bóng Mực choáng | Không di chuyển, không gây sát thương. Trạng thái `stunned`, còn lại là `chase` |
| A8 | Thua | Hết flames (`no_flames`) hoặc hết giờ Đêm 1 = 300 s (`dawn`) |
| A9 | Rơi khỏi đảo | `fall_enabled = false`: người chơi bị giữ trong bán kính đảo 40 m. Không có sự kiện `by: "fall"` |
| A10 | Nhảy | Vận tốc 7 m/s, trọng lực 20 m/s². Chỉ là cảm giác chơi: khoảng cách tính theo XZ nên nhảy **không** né được Bóng Mực |
| A11 | Bố trí màn | 5 đèn trên vòng tròn bán kính 25 m, L1 ở (0,0,25), mỗi đèn cách nhau 72°. 30 đom đóm ngẫu nhiên trong vành 3–38 m, cứ 3 s sinh thêm 1 con nếu đang ít hơn 30. 2 Bóng Mực ở bán kính 36 m, cứ 30 s sinh thêm 1 con, tối đa 5 (sự kiện `shade_spawned`) |
| A12 | Thứ tự xử lý trong 1 tick | timers → di chuyển/nhảy → nhặt → interact → pulse → Bóng Mực di chuyển → va chạm → sinh mới → kiểm tra bình minh. Thắng hoặc thua thì dừng ngay trong tick đó |
| A13 | Input sai miền giá trị | `move` ngoài [−1,1], tick không tăng nghiêm ngặt, sai kiểu dữ liệu, id đèn lạ → exit 2. `--night` khác 1 → exit 2 |
| A14 | Snapshot | Chỉ ghi ở tick là bội của `--snapshot-every`. Không ghi thêm snapshot cuối, vì dòng `end` đã có state và score |

## 3. Cách tính điểm

| Sự kiện | Điểm |
|---|---|
| Nhặt 1 đom đóm | +10 (`per_mote`) |
| Thắp 1 đèn | +100 (`per_lantern`) |
| Mỗi Bóng Mực bị choáng trong 1 lần pulse | +20 (`per_stun`) |
| Khi **thắng**: mỗi giây còn lại (làm tròn xuống) | +1 (`per_second_left`) |
| Khi **thắng**: mỗi flame còn lại | +50 (`per_flame_left`) |

Thua thì không có thưởng cuối màn.

## 4. Tiêu chí nghiệm thu

| ID | Tiêu chí (làm A thì thấy B) |
|---|---|
| R1 | `move [0,1]` trong 60 tick, yaw 0 → z tăng `player_speed` m. Yaw 90 → đi theo +X. `[1,1]` được chuẩn hóa |
| R2 | Đom đóm cách ≤ `pickup_radius` → `mote_picked`, carried +1, score +10. Khi đầy `carry_capacity` thì không nhặt |
| R3 | Interact gần đèn → `deposit`. Đủ 10 → `lantern_lit`, +100. Giữ nút nhiều tick chỉ nạp 1 lần |
| R4 | Thắp đủ 5 đèn → `game_over won all_lit`, dòng `end` có state `won` |
| R5 | Bóng Mực đuổi với `shade_speed`. Chạm (≤ 1 m) → `player_hit`, flames −1, rơi đom đóm, sau đó bất tử 1.5 s |
| R6 | Flames = 0 → `lost no_flames`. Hết giờ → `lost dawn` |
| R7 | Pulse → choáng, đẩy lùi, tốn đom đóm, có hồi chiêu. Choáng đúng 3 s |
| R8 | Bóng Mực không vào vùng `safe_radius` của đèn đã thắp |
| R9 | Snapshot ở tick 0 và mỗi N tick. Sự kiện ghi tick = k+1. `end` là dòng cuối |
| R10 | Cùng seed, scenario, inputs → output giống hệt từng byte |
| R11 | File sai định dạng → exit 2 kèm thông báo trên stderr |
| R12 | Bản 3D chơi được Đêm 1 từ đầu tới thắng/thua, có HUD, chơi lại được |
