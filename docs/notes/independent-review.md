# Đánh giá độc lập (reviewer không viết mã này)

Người đánh giá: một agent Claude độc lập, không tham gia viết code. Căn cứ: bản tóm tắt ticket (số liệu giữ nguyên văn), `docs/lab/RUBRIC.md` và mã ở `main` (commit ebfea67, Contract v1.3). Mọi phép thử chạy trên thư mục tạm, không sửa file nào trong repo. Script thử nằm ngoài repo và gọi `lantern.headless.run(...)`, tức cùng đường chạy với CLI.

## Tóm tắt

- Luật lõi v1.2/v1.3 khớp spec ở hầu hết các điểm đã thử:
  - thứ tự tick, gồm cả việc đốt dầu ở bước 2 và đèn tắt ngay sau đó;
  - thắng/thua lúc bình minh;
  - Tỏa Sáng (bán kính 3D, đẩy lùi 4 m trong 15 tick);
  - chọn đèn khi khoảng cách bằng nhau;
  - lịch sinh Bóng Mực;
  - mã thoát;
  - tính tất định.
- 109 unit test đều đạt (`python -m unittest discover -s tests`, khoảng 16 s).
- Đã xác nhận **2 lệch luật nhỏ** về vật lý nhảy và **1 lỗi trong quy trình tag**: `run_cmd` không chạy được ở phase-1..3.
- Rủi ro lớn nhất với test ẩn nằm ở các **giả định** mà spec không quy định, nhất là tốc độ `wander` = 2 m/s.

## Lỗi đã xác nhận

### L1. Bấm nhảy trong lúc lướt trên mặt đất thì cú nhảy bị nuốt mất. Mức độ: thấp đến trung bình

- Vị trí: `lantern/sim.py:544-546` (nhảy đặt `grounded=False`), sau đó `sim.py:563-564` (`dashing and not grounded` thì đặt `vel_y = 0`).
- Cách tái hiện: scenario rỗng (`random_* = false`), inputs `[{"tick":0,"jump":true,"dash":true}]`, chạy 30 tick, `--snapshot-every 1`. Biến thể: lướt ở tick 0, nhảy ở tick 3.
- Kỳ vọng: spec nói "jump only when grounded", mà người chơi đang đứng đất nên phải nhảy được (Y lên khoảng 1.2 m).
- Thực tế: `maxY = 0.0` ở cả hai biến thể. Khi chỉ nhảy ở tick 3 (không lướt) thì `maxY = 1.167`. Sự kiện `dash` vẫn được ghi.

### L2. Tích phân nhảy làm đỉnh nhảy và thời gian trên không lệch so với v=7, g=-20. Mức độ: trung bình

- Vị trí: `lantern/sim.py:565-566` và `575`. Đây là semi-implicit Euler: trọng lực được trừ vào vận tốc ngay trong tick nhảy, trước khi cập nhật vị trí.
- Cách tái hiện: inputs `[{"tick":0,"jump":true}]`, chạy 60 tick, `--snapshot-every 1`.
- Kỳ vọng (giải tích): đỉnh 7²/(2·20) = **1.225 m**, thời gian trên không **0.7 s = 42 tick**.
- Thực tế: đỉnh **1.167 m** và chạm đất ở tick **41**.
- Test `tests/test_rules.py:97` dùng `delta=0.06`, chỉ vừa đủ chứa sai số 0.058. Một test ẩn dùng dung sai 0.05 sẽ đỏ. `docs/notes/phase-2-spec.md` (P2-1) ghi "≈ 1.225 m" là chưa chính xác.

### L3. `run_cmd` ở tag phase-1, phase-2, phase-3 trỏ tới module không tồn tại. Mức độ: trung bình (rubric F/A theo tag)

- Cách tái hiện: `git ls-tree --name-only phase-1 lantern/` chỉ trả về `__init__, config, contract_io, headless, sim`; phase-2 và phase-3 thêm `maps`.
- Kỳ vọng: `run_cmd` là `.venv/bin/python -m lantern.app` và chạy được ở mọi tag.
- Thực tế: ở 3 tag này không có `lantern/app.py`, nên `run_cmd` lỗi. README ở tag phase-1 vẫn hướng dẫn "`.venv/bin/python -m lantern.app # chơi`". Phần proof của phase-1 thì ghi trung thực "Chưa đạt (chưa có client 3D)".

### L4. Kiểm tra đột biến cho thấy test bỏ sót một số điểm biên. Mức độ: thấp (chất lượng bằng chứng)

Tôi sửa thử `sim.py` trên một bản sao tạm rồi chạy toàn bộ unit test:

| Đột biến | Kết quả |
|---|---|
| chọn đèn bằng nhau: `<` thành `<=` | test đỏ (tốt) |
| điểm pulse khi đang drain: 15 thành 20 | test đỏ (tốt) |
| ngưỡng thắng: `ceil` thành `floor` | test đỏ (tốt) |
| vùng an toàn: `fuel >= 30` thành `> 30` | **vẫn đạt**: `test_exactly_30_keeps_safe_zone` không bao giờ quan sát đúng lúc fuel = 30 |
| đom đóm rơi nhặt được ngay trong tick rơi | **vẫn đạt** |
| thưởng bình minh: `floor(fuel)` thành `round(fuel)` | **vẫn đạt**: test dùng fuel nguyên 99.0 |

Đây không phải bằng chứng giả, nhưng các test này yếu đúng ở những điểm biên mà spec ghi rõ.

## Rủi ro giả định (test ẩn có thể hiểu khác)

| # | Điểm mơ hồ | Cách repo đang làm | Rủi ro |
|---|---|---|---|
| R1 | Tốc độ Bóng Mực khi `wander` | 2.0 m/s (`config.py:36`, giả định A). Spec chỉ ghi "speed 4.0" | **Cao**: mọi test T03 về shade đi tới đèn yếu rồi drain sẽ lệch thời điểm gấp đôi. Scenario 22 tính drain ở tick 241 là theo 2 m/s |
| R2 | Châm dầu ngay ở tick 0 | Dầu hao ở bước 2 trước khi interact ở bước 5. Fuel 50 thành 49.983, nên `used = ceil(5.0017) = 6`, không phải 5 (đã chạy: `refuel amount 6`, điểm 30) | Trung bình: đúng chữ theo thứ tự tick, nhưng người viết test có thể nhẩm ra 5 |
| R3 | "+15 total" khi pulse trúng con đang drain | Con đang drain được 15 thay cho 5 (đã chạy: điểm 15) | Trung bình: có thể hiểu là 5 + 15 = 20 |
| R4 | Snapshot `player.invuln` | Số giây (1.5), không phải tick hay bool | Trung bình |
| R5 | Điểm xuất phát Đêm 3 | (0, 0, −30) (`maps.py:66`) | Trung bình: spec chỉ ghi start cho Đêm 1 |
| R6 | Trạng thái `spawning` | 60 tick, đứng yên, vô hại (`config.py:37`) | Trung bình: lệch thời gian đuổi và chạm sau tick 300 |
| R7 | Tâm Bóng Mực khi tính bán kính pulse 3D | Dùng `pos` (chân). Với chênh cao 0.8, bán kính ngang thực tế là 4.936 m (XZ 4.93 trúng, 4.936 trượt, 5.0 trượt) | Thấp đến trung bình |
| R8 | Snapshot cuối khi game kết thúc giữa chu kỳ | Không ghi thêm snapshot. Ví dụ kết thúc ở tick 15 thì snapshot cuối là tick 10 (`headless.py:30-33`) | Thấp đến trung bình |
| R9 | Scenario có `motes` nhưng `random_motes` mặc định | Vẫn sinh thêm đom đóm ở tick 240 | Thấp |
| R10 | Shade đang bị đẩy khỏi vùng an toàn | Hiện `state: "recoil"` | Thấp |
| R11 | Soak | Chỉ chạy sim headless, không có client 3D. Không có trường `pass` | Thấp đến trung bình (hạng mục E) |
| R12 | `build_cmd` / `headless_cmd` | Chỉ chạy trên POSIX (`python3`, `.venv/bin`). Không chạy trên Windows | Thấp (CI chạy macOS/Linux) |

## Kiểm tra bằng chứng

**Các phép thử headless có chủ đích (đều khớp spec):**

| Luật | Kết quả |
|---|---|
| Đèn fuel 0.5 | Tắt ở tick 30, phát `lantern_out` |
| Fuel 30.05 | Mất vùng an toàn sau 3 tick |
| Bình minh với 3 đèn sáng, fuel 30.5 / 100 / 2, 3 lửa | `won dawn_survived`, điểm **429** = (50+29) + (50+99) + (50+1) + 3·50. Đúng như tôi tính tay |
| L3 fuel 0.99 | Tắt ở tick 59, còn 2/5 đèn nên `lost dawn` (đúng: tính số đèn ở tick cuối) |
| Mất lửa cuối ở cùng tick hết giờ | `no_flames` được xét trước (đúng) |
| Pulse | Đẩy shade từ x=3 tới x=7 trong tick 1..15; choáng 120 tick; cooldown 180 tick |
| Bất tử | Bị chạm ở tick 1, 91, 181 |
| Chọn đèn | Bằng khoảng cách thì chọn L1 |
| Lịch sinh Bóng Mực | Đêm 1: S1, S2 ở tick 300, rồi 780, 1260…, tối đa 6. Đêm 2 cách 420 tick, tối đa 8. Đêm 3 cách 360 tick. Id tiếp nối sau id có sẵn trong scenario |
| Rơi khỏi đảo | Rơi ở tick f, hồi sinh ở f+60 với `invuln` 1.5 s |
| Pause | Đúng cả hai: tick tăng, sim_tick đứng yên |
| Mã thoát | 2 cho JSON hỏng, tick không tăng dần, move ngoài [-1,1], nút không phải bool, id đèn sai, `--night 4`, file thiếu. 1 cho đường dẫn `--out` hỏng |

**Tính tay 3 file expect.json (đều khớp):**

- `21_relight`: đèn `ever_lit`, mang 7 đom đóm, chi phí 5 → 5·5 + 40 = **65**.
- `23_dawn_survived`: 3 đèn fuel 100, 60 tick → fuel 99 → 3·(50+99) + 2·50 = **547**, `ticks` 60.
- `22_drain`: shade cách đèn 10 m đi với 2 m/s thì tới khoảng cách 2 m sau 240 tick, drain từ tick 241. Fuel lúc đó 25 − 241/60 = 20.98, hao 6/s nên đèn tắt khoảng tick 451. Có 3 sự kiện `fuel_drain` ở tick 301, 361, 421. Khớp danh sách sự kiện trong expect.

**Hạn chế của các scenario:**

- 06 và 15 chỉ kiểm tra tính tất định và mã thoát.
- 09, 10, 16 chỉ kiểm tra danh sách sự kiện `["night_start"]`, nên không chứng minh được nhảy đáp đúng tầng hay có gió. Các ý này đã có unit test bổ sung, và tôi đã tự kiểm lại: bục Đêm 2 đáp ở tick 84 ≈ 1.4 s; bục Đêm 3 đáp ở Y=6.

**Proof phase-4:** ghi trung thực, có nêu lần bench p1_low 26.6 < 30. Riêng `docs/proof/phase-4/scenarios.md` đang bị sửa mà chưa commit (chỉ khác thời gian chạy). Nên commit hoặc khôi phục, để file khớp với tag.

## Thiếu sót theo rubric

- **F/A theo tag:** ở phase-1..3 không có bản 3D chơi được, và `run_cmd` hỏng (L3). Phần F của các phase đầu sẽ mất điểm.
- **B (test):** còn khe hở biên (L4). Test nhảy có dung sai nới vừa khít (L2). Một số scenario chỉ so danh sách sự kiện.
- **C (Git):** có vài commit rất lớn, ví dụ "Add Ursina 3D client: menu, 3-night flow, HUD…". Chưa đúng tinh thần "commit nhỏ".
- **E:** p1_low_fps dao động quanh ngưỡng 30 trên máy tác giả. Soak không chạy client đồ họa.
- **B ("đánh giá do người/agent khác"):** trước bản review này chưa có reviewer độc lập. File này bổ sung phần đó.
- **G/F:** proof tự nhận ảnh chụp là do bot tạo. Cần bằng chứng có người thật chơi bằng bàn phím trong video.

## Kết luận

Engine headless bám spec tốt: không tìm thấy lỗi nghiêm trọng ở các luật được chấm nặng (fuel, bình minh, pulse, lịch sinh, tie-break, mã thoát). Nên làm, theo thứ tự ưu tiên:

1. Xem lại R1 (tốc độ `wander`). Đây là rủi ro lớn nhất với test ẩn T03.
2. Sửa L1: cho phép nhảy khi đang lướt trên đất. Chỉ ép `vy = 0` nếu lúc bắt đầu lướt người chơi đang ở trên không.
3. Cân nhắc tích phân chính xác cho bước nhảy (L2), rồi siết dung sai của test.
4. Thêm test biên: fuel đúng bằng 30, `floor(fuel)` với fuel lẻ, đom đóm rơi chỉ nhặt được từ tick sau.
5. Ghi rõ trong README/proof rằng `run_cmd` không dùng được ở các tag phase-1..3.
