# Ghi chú phân tích · Day 04

Họ và tên: [Họ và tên sinh viên]
MSSV: [MSSV]

## 1. Case được chọn

- ID case: Reproducer của validation-source bug trong `tests/test_validation.py` (bài toán thiếu URL khi đã đọc chi tiết incident).
- Câu trả lời của agent: "Incident đã xử lý." / câu trả lời cuối không chứa URL nguồn đã lấy từ `get_incident_details`.
- Điểm ở lần chạy 1: null trong eval tổng thể vì không có provider/model thực tế để chấm; tuy nhiên, bug này đã được tái hiện và sửa bằng local unit test. Local validation: `python -m unittest discover -s tests -v` -> pass (40 tests).

## 2. Bằng chứng trong trace

Đây là trace mẫu mô phỏng lỗi từ unit test và từ logic trong `agent.py` (sau khi bug được tái hiện):

```text
{"event":"tool","step":1,"name":"get_incident_details","result":{"ok":true,"id":"xr3myzj7ms51","url":"https://stspg.io/pjgptg3cfc6n"}}
{"event":"validation_missing_source","step":2}
{"role":"user","content":"Câu trả lời thiếu URL nguồn incident đã quan sát. Hãy bổ sung URL incident vào câu trả lời."}
```

Nguyên nhân: agent có thể gọi `get_incident_details` thành công, nhưng nếu final answer không chứa URL đã quan sát thì không có cơ chế buộc model sửa lại. Đặc biệt, khi prompt/schema của tool set thay đổi (bonus tools), agent vẫn hard-code `SCHEMAS` và `SYSTEM_PROMPT` cũ, nên không tương thích với tool mới và có thể trả lời thiếu bằng chứng. Điều này làm mất tính nhất quán giữa evidence và final answer.

## 3. Thay đổi đã thực hiện

- Sửa ở: `agent.py`
- Thay đổi cụ thể:
  - dùng `system_prompt = getattr(tools, 'system_prompt', SYSTEM_PROMPT)`
  - dùng `schemas = getattr(tools, 'schemas', SCHEMAS)`
  - giữ nguyên validation nguồn cho final answer: nếu có incident URL thành công nhưng câu trả lời thiếu URL thì ghi `validation_missing_source` vào trace và yêu cầu model sửa trong budget còn lại.
  - vẫn giữ compatibility với tools bài chính (`StatusTools`) và bonus tools (`BonusTools`).

Vì sao chọn thay đổi này: vì đây là lỗi có căn cứ rõ ràng trong trace và có test kiểm tra trực tiếp (`tests/test_validation.py`). Nó trực tiếp giải quyết vấn đề "bằng chứng tách khỏi câu trả lời cuối" và giúp agent thích nghi với tool set khác nhau mà không hard-code định nghĩa tool.

## 4. So sánh hai lần chạy

| Chỉ số | `eval_before.json` | `eval_after.json` |
|---|---|---|
| Điểm tổng | null | null |
| Điểm case đã chọn | local reproducer fail trước khi sửa; judge không chấm do thiếu key | local reproducer pass sau khi sửa; judge vẫn null |
| Số model calls | 0 trong eval thực tế vì không có API key hợp lệ | 0 trong eval thực tế vì không có API key hợp lệ |
| Token, chi phí nếu có | Không có | Không có |

- Lỗi đã giải quyết: thiếu check nguồn URL trong final answer; không tương thích với `tools.system_prompt`/`tools.schemas` khi dùng bonus tool set.
- Lỗi còn lại hoặc mới xuất hiện: không có `GEMINI_API_KEY` / `OPENAI_API_KEY` / model hợp lệ nên eval LLM judge không thể chạy được trên máy này; vì vậy điểm tổng của cả hai lần vẫn là `null` và chỉ có thể dựa vào unit tests để đánh giá logic agent.

## 5. Giới hạn

- Điểm judge chỉ là ước lượng và chỉ đáng tin khi có model/provider thật, quota hợp lệ và câu hỏi được chấm đúng chuẩn. Do key bị rate limit nên toàn bộ `eval_before.json`/`eval_after.json` bị unscored.
- Snapshot là dữ liệu tĩnh, không phản ánh trạng thái live thực tế. Cùng một snapshot có thể không còn đúng với thời điểm user hỏi khi chạy live.
- Chỉ chạy một lần mỗi phiên bản không thể khẳng định độ ổn định. Cần nhiều lần chạy, cùng cấu hình, và so sánh trace & cost để phát hiện lỗi ngẫu nhiên hoặc prompt drift.
- Trên môi trường Windows, khi chạy `evals/run_evals.py` với output chứa tiếng Việt, cần dùng `python -X utf8 ...` để tránh lỗi mã hóa Unicode trong terminal. Đây là giới hạn cài đặt, không phải lỗi logic của agent.
