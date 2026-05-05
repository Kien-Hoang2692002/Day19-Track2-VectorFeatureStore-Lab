# Reflection — Lab 19

**Tên:** _Hoàng Văn Kiên_
**Cohort:** _<A20-K1 / A20-K2 / ...>_
**Path đã chạy:** _<lite>_

---

## Câu hỏi (≤ 200 chữ)

> Trên golden set 50 queries, mode nào thắng ở loại query nào (`exact` /
> `paraphrase` / `mixed`), và tại sao? Khi nào bạn **không** dùng hybrid
> (i.e. khi nào pure BM25 hoặc pure vector là lựa chọn đúng)?

Trên golden set 50 queries, mode nào hiệu quả phụ thuộc vào loại query và ngữ cảnh cụ thể. Dưới đây là một số nhận xét về từng loại query:

Exact: Mode exact phù hợp với các query yêu cầu tìm kiếm chính xác các từ hoặc cụm từ trong văn bản. Ví dụ: "Việt Nam" hoặc "công nghệ thông tin". Trong trường hợp này, pure BM25 hoặc pure vector embeddings có thể là lựa chọn đúng vì chúng tập trung vào việc tìm kiếm các từ hoặc cụm từ chính xác trong văn bản.
Paraphrase: Mode paraphrase phù hợp với các query yêu cầu tìm kiếm các văn bản có nội dung tương tự hoặc có ý nghĩa tương đương. Ví dụ: "công nghệ thông tin tương lai" hoặc "việt nam phát triển như thế nào". Trong trường hợp này, hybrid mode có thể là lựa chọn đúng vì nó kết hợp giữa BM25 và vector embeddings để tìm kiếm các văn bản có nội dung tương tự hoặc có ý nghĩa tương đương.
Mixed: Mode mixed phù hợp với các query có sự kết hợp giữa các loại query exact và paraphrase. Ví dụ: "việt nam công nghệ thông tin tương lai". Trong trường hợp này, hybrid mode có thể là lựa chọn đúng vì nó có thể xử lý được cả exact và paraphrase.
Tuy nhiên, lựa chọn mode phụ thuộc vào ngữ cảnh cụ thể và yêu cầu của hệ thống tìm kiếm. Khi nào không nên dùng hybrid mode là khi pure BM25 hoặc pure vector embeddings đã đủ để đáp ứng yêu cầu tìm kiếm. Ví dụ: khi chỉ cần tìm kiếm các văn bản có nội dung chính xác hoặc khi hệ thống đã được tối ưu hóa cho pure BM25 hoặc pure vector embeddings.
## Điều ngạc nhiên nhất khi làm lab này

Điều ngưỡng nhiên nhất khi làm bài lab này là hiểu rõ về các khái niệm và công nghệ liên quan. Điều này bao gồm:

Hiểu rõ về tìm kiếm thông minh và cách nó hoạt động.
Hiểu rõ về Qdrant và cách sử dụng nó để xây dựng hệ thống tìm kiếm.
Hiểu rõ về vector embeddings và cách sử dụng chúng để tạo index và tìm kiếm.
Hiểu rõ về triển khai API và cách sử dụng nó để tìm kiếm với các mode khác nhau.
---

## Bonus challenge

- [ ] Đã làm bonus (xem `bonus/`)
- [ ] Pair work với: _<tên đồng đội nếu có>_
