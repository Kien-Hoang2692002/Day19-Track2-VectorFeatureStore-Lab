# Hybrid Memory POC for Vietnamese Personal AI Assistant

_Contributors: Hoàng Văn Kiên_

## Goal

POC này mô phỏng một trợ lý AI cá nhân cho người dùng Việt Nam, kết hợp hai lớp
memory có vòng đời khác nhau:

- **Episodic memory** lưu cuộc hội thoại, tài liệu đã đọc, note người dùng tự
  lưu. Dạng dữ liệu này tăng nhanh, mang tính ngữ nghĩa, nên phù hợp với
  **vector store** để semantic retrieval.
- **Stable profile + recent activity** lưu các feature có cấu trúc như ngôn ngữ
  ưu tiên, tốc độ đọc, chủ đề quan tâm, active hours, queries 1 giờ qua. Đây là
  dữ liệu phục vụ personalization và freshness, nên phù hợp với **feature
  store** và streaming feature view.

Thiết kế chọn mô hình **hybrid retrieval**: vector store trả về “người dùng đã
  từng đọc / nói gì”, còn feature store trả về “người dùng là ai và đang ở
  trạng thái nào”. LLM hoặc response layer sẽ hợp nhất cả hai để tạo câu trả
  lời cuối.

## Architecture Diagram

```text
                 +----------------------+
                 |   User Interaction   |
                 | chat / docs / notes  |
                 +----------+-----------+
                            |
             +--------------+--------------+
             |                             |
             v                             v
  +-----------------------+      +------------------------+
  | Episodic ingest path  |      | Profile/activity path  |
  | chunk -> embed        |      | parse events/features  |
  +-----------+-----------+      +-----------+------------+
              |                              |
              v                              v
   +------------------------+      +-----------------------+
   | Qdrant / Vector Store  |      | Feast Online Store    |
   | payload: user_id,      |      | stable + streaming    |
   | source, ts, topic      |      | features per user     |
   +-----------+------------+      +-----------+-----------+
               \                            /
                \                          /
                 v                        v
                +--------------------------+
                |   HybridMemoryAgent      |
                | 1. get profile/features  |
                | 2. vector search top-K   |
                | 3. assemble context      |
                +-------------+------------+
                              |
                              v
                    +------------------+
                    | LLM / Response   |
                    | final answer     |
                    +------------------+
```

## Decision 1: Chunking Strategy

Tôi chọn **semantic chunking theo đoạn ngắn 120–220 token, có overlap nhẹ
20–40 token**, thay vì chỉ lưu per-message hoặc nguyên conversation.

Lý do:

- **Per-message** rất rẻ về ingest, dễ map ngược ra nguồn, nhưng retrieval kém
  khi một ý quan trọng trải dài qua 2–3 tin nhắn hoặc nằm trong một đoạn tài
  liệu dài.
- **Per-conversation / per-document** giảm số vector và có thêm context tổng
  thể, nhưng dễ lãng phí context window vì mỗi hit kéo theo nhiều câu không liên
  quan. Điều này làm recall “trợ lý nhớ gì về Kubernetes?” kém chính xác khi
  trong cùng conversation còn có Docker, CI/CD, Terraform.
- **Semantic break + token cap** cân bằng hơn: đủ nhỏ để retrieval chính xác,
  đủ lớn để giữ nghĩa cục bộ, và storage cost vẫn chấp nhận được cho POC.

Tradeoff explicit:

- **Retrieval quality**: semantic chunk > per-conversation cho truy vấn hẹp và
  paraphrase.
- **Storage cost**: semantic chunk tốn vector hơn per-conversation.
- **Context window efficiency**: semantic chunk tốt hơn vì top-K ít nhiễu hơn.

Với tiếng Việt, semantic chunking còn quan trọng vì một ý có thể dài và ít dấu
chấm hơn tiếng Anh. Nếu split quá cơ học theo số câu, hệ thống dễ cắt mất ngữ
cảnh “mở rộng tự động hạ tầng” và “autoscaling” là cùng một chủ đề.

## Decision 2: Feature Schema

Tôi chọn **tabular online features làm lớp chính**, và chỉ dùng embedding ở lớp
episodic memory chứ không dùng “embedding features” làm profile mặc định.

Schema đề xuất cho entity `user_id`:

- `preferred_language`: `vi | en | mix`, TTL 30 ngày, source từ lịch sử chat và
  explicit user setting.
- `reading_speed_wpm`: số nguyên, TTL 14 ngày, source từ hành vi đọc / thời
  lượng ở notebook.
- `topic_affinity_cloud`, `topic_affinity_ai`, `topic_affinity_security`: số
  thực 0–1, TTL 7 ngày, source từ aggregate docs + queries.
- `active_hour_bucket`: ví dụ `early_morning | office_hours | late_night`, TTL
  7 ngày, source từ event timestamps.
- `queries_last_hour`: danh sách rút gọn, TTL 1 giờ, source từ streaming
  pipeline.
- `fatigue_signal`: boolean hoặc score, TTL 1 giờ, source từ pattern query dài
  hơn vào buổi tối.

Tại sao không chọn embedding features cho profile?

- Tabular features **dễ giải thích**, dễ debug, dễ join online, phù hợp với
  personalization rule kiểu “nếu language=mix thì trộn vi/en”.
- Embedding profile có thể nén latent preference tốt hơn, nhưng khó kiểm soát,
  khó audit, và không rõ feature nào đang ảnh hưởng response. Với POC cần cho
  giảng viên thấy **judgment**, tabular features rõ ràng hơn.

Tôi có xem xét cách lưu cả episodic memory vào feature store dưới dạng embedding
feature view, nhưng loại bỏ lựa chọn này. Lý do là **re-index cycle và access
pattern khác hẳn**: episodic memory cần top-K ANN search, append liên tục,
payload filtering; còn profile features cần point lookup rất nhanh, có TTL/PIT
join rõ ràng. Tách vector store và feature store giúp mỗi lớp tối ưu đúng việc
của nó.

## Decision 3: Freshness Strategy

Tôi không chọn một mức freshness duy nhất cho mọi thứ; tôi chọn **phân tầng theo
use case**:

1. **Sub-second gần real time** cho `queries_last_hour` và `fatigue_signal`.
   Use case: user hỏi “Tôi đang quan tâm gì gần đây?” hoặc hệ thống muốn điều
   chỉnh tone vì user đang mệt về đêm. Đây là dữ liệu hành vi ngắn hạn, giá trị
   giảm rất nhanh, nên cần streaming feature view / Push API.
2. **1–5 phút** cho cập nhật `topic_affinity` và recent read summaries. Use
   case: user vừa đọc xong vài trang về cloud security rồi hỏi “Recommend đọc gì
   tiếp”. Không nhất thiết sub-second, nhưng cũng không nên chờ daily batch.
3. **Daily hoặc on-write refresh** cho stable profile như `preferred_language`,
   `reading_speed_wpm`, `active_hour_bucket`. Những feature này thay đổi chậm,
   nên cập nhật quá dày làm tăng compute mà không tăng đáng kể chất lượng.

Vì vậy, nếu user vừa đọc xong một tài liệu mới, truy vấn “trợ lý nhớ gì về tôi?”
trong POC nên phản ánh:

- **Ngay gần tức thời** ở phần recent activity.
- **Sau vài phút** ở phần topic affinity / summary.
- **Không cần ngay** ở phần profile ổn định.

## Vietnamese-Context Considerations

Có ba điểm đặc thù cho người dùng Việt Nam:

- **Code-switching vi/en**: nhiều query như “summary cloud security giúp mình”.
  Vì vậy payload và profile cần lưu `preferred_language=mix`; retrieval không
  nên giả định ngôn ngữ đơn nhất.
- **Phonetic typo / không dấu**: “bao mat dam may”, “kuberbetes”, “autoscaling
  ha tang”. POC tối thiểu có thể chuẩn hóa lowercase, bỏ ký tự thừa, giữ thêm
  từ khóa alias tiếng Anh cho mỗi memory. Ở bản production nên cân nhắc
  tokenizer / normalization tốt hơn.
- **Tokenizer choice**: whitespace split rẻ và đơn giản nhưng yếu cho cụm ghép
  tiếng Việt; `pyvi` hay `underthesea` có thể cải thiện segmentation nhưng tăng
  dependency và latency. Với POC, tôi giữ tokenizer đơn giản + semantic overlap;
  với production, tôi sẽ benchmark tokenizer theo recall@k trên tập query vi/en
  mix.

Ngoài NLP, còn có **privacy**: dữ liệu cá nhân của user Việt Nam nên được thiết
  kế với nguyên tắc tối thiểu hóa dữ liệu, phân tách theo `user_id`, và có khả
  năng xóa / hết hạn theo yêu cầu. Điều này quan trọng khi xét đến bối cảnh tuân
  thủ dữ liệu cá nhân như Decree 13.

## Lab Concept Mapping

- **Vector store**: lưu episodic memory, filtered theo `user_id`.
- **Feature store**: lưu stable profile và online features.
- **TTL**: áp dụng cho recent activity và một phần affinity.
- **Streaming**: cập nhật `queries_last_hour`, `fatigue_signal`.
- **PIT join mindset**: nếu offline training sau này, feature values phải tương
  ứng đúng thời điểm event để tránh leakage.
- **Hybrid retrieval / re-ranking**: POC mới assemble context; bản sau có thể
  re-rank top-50 vector hits bằng `topic_affinity` hoặc dùng RRF giữa semantic
  retriever và profile-aware retriever.

## What This POC Doesn't Handle Yet

- Chưa có Qdrant/Feast thật; dùng in-memory mock để làm rõ flow.
- Chưa có CRUD / delete memory theo user request.
- Chưa mã hóa dữ liệu at rest hoặc multi-device sync.
- Chưa có privacy isolation cứng hơn như per-user collection hoặc per-user key.
- Chưa có consolidation / forgetting policy cho memory cũ.
- Chưa gọi LLM thật; `recall()` mới trả về assembled context để demo thiết kế.

## Optional Workflow Note

Prompt hiệu quả nhất khi làm bài kiểu này là prompt buộc AI so sánh **X vs Y vs
Z với tradeoff định lượng hoặc operational** thay vì chỉ “viết architecture”.
Prompt fail phổ biến là yêu cầu AI “thiết kế memory system hoàn chỉnh” quá rộng,
kết quả thường dài nhưng thiếu quyết định cụ thể về TTL, freshness và schema.
