# ADR 0001: Mô hình nhiên liệu đèn và luật thắng "giữ đảo sáng tới bình minh"

- **Trạng thái:** Chấp nhận, áp dụng từ Phase 3 (Ticket-03, Contract v1.2)
- **Thay thế:** luật "đèn sáng là vĩnh viễn" và "thắng ngay khi tất cả đèn sáng" (Ticket-02)

## Bối cảnh

Ticket-03 cho rằng game hết căng thẳng khi người chơi giỏi thắp xong đèn trong khoảng 2 phút. Vì vậy đèn phải có thể tắt, và mục tiêu chuyển sang giữ đủ số đèn sáng cho tới bình minh.

## Quyết định

1. **Trạng thái đèn** chuyển từ `{lit, deposited}` sang `{lit, deposited, fuel, ever_lit, relit_count}`:

   ```text
   unlit(ever_lit=false) --nạp đủ 10--> lit(fuel=100) --fuel<=0--> unlit(ever_lit=true) --nạp đủ 5--> lit(fuel=100, relit_count+1)
   lit --châm dầu--> lit(fuel += 10 mỗi đom đóm, tối đa 100)
   ```

   Đèn sáng có `fuel < 30` mất vùng an toàn. Đúng bằng 30 vẫn giữ vùng an toàn.

2. **Dầu lưu bằng số nguyên với đơn vị 1/60** (`FU = 60`, max = 6000). Hao 1/s thành −1 FU mỗi tick, bị hút 5/s thành −5 FU mỗi tick mỗi con. Không có sai số số thực, và output tất định trên mọi máy. Chỉ đổi ra số thực khi xuất (`round(fu/60, 1)`).

3. **Vị trí trong tick:** thêm bước 2b ngay sau bước 2 của Ticket-02, gồm trừ dầu (hao + hút), rồi tắt các đèn có fuel ≤ 0 (`lantern_out`). Sự kiện `fuel_drain` ghi mỗi 60 tick hút của từng con.

4. **Bóng Mực có thêm trạng thái `drain`.** `wander` ưu tiên đèn yếu (`fuel < 30`, gần nhất, bằng nhau thì id nhỏ hơn). Không có đèn yếu thì đi về đèn tắt gần nhất như trước. Khi cách đèn ≤ 2 m thì chuyển `drain` và đứng yên. Rời `drain` khi:
   - Mây vào trong 6 m → `chase`;
   - trúng pulse → `stunned`;
   - đèn tắt, được châm lên ≥ 30, hoặc nó cách đèn > 2 m → `wander`.

   Châm dầu đưa đèn từ dưới 30 lên ≥ 30 thì dùng lại cơ chế đẩy ra mép của lúc vừa thắp đèn (`_evict_from`).

5. **Luật thắng** chuyển vào bước 11 và chỉ xét khi hết giờ: thứ tự là `no_flames` trước, rồi đủ `ceil(0.6 × số đèn)` thì `dawn_survived`, còn lại là `dawn`. Xóa hẳn nhánh `all_lit`.

6. **Sức chứa** đổi thành một thuộc tính tính được: `min(20, 10 + 2 × successful_lights)`. Không lưu riêng, để không bao giờ lệch với số lần thắp.

7. **Điểm:** các khóa mới nằm trong `tuning.score` (`per_relight`, `per_drain_stun`, `per_lit_at_dawn`). `per_mote` = 5 và `per_second_left` = 0, nên số liệu vẫn chỉ có một nguồn duy nhất là `game.contract.json`.

## Hệ quả

- Các test và scenario của Phase 1–2 về `all_lit` và điểm cũ đã được **sửa kèm lý do** (đánh dấu `# T03`, xem [CHANGELOG](../../CHANGELOG.md)). Không test nào bị skip.
- Một Đêm luôn chạy đủ thời lượng nếu Mây còn sống. Hiệu năng vẫn đạt: Đêm 3 với 18.000 tick chạy khoảng 2 s.
- Đánh đổi: trạng thái `drain` khiến luồng di chuyển của Bóng Mực có thêm một nhánh. Mình chấp nhận vì cả 5 điều kiện chuyển trạng thái đều có test riêng trong `tests/test_phase3.py`.
