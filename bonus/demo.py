from agent import HybridMemoryAgent


def seed_memories(agent: HybridMemoryAgent, user_id: str) -> None:
    agent.remember(
        "Tôi đã đọc tài liệu Kubernetes cơ bản, bao gồm pod, deployment, service "
        "và cách cluster tự phục hồi khi node có lỗi.",
        user_id=user_id,
    )
    agent.remember(
        "Ghi chú về cloud security: IAM least privilege, mã hóa dữ liệu at rest, "
        "audit log, zero trust và network segmentation cho workload nhạy cảm.",
        user_id=user_id,
    )
    agent.remember(
        "Tài liệu về tự động mở rộng hạ tầng giải thích horizontal autoscaling, "
        "metrics CPU, queue depth và khi nào nên scale theo lịch.",
        user_id=user_id,
    )
    agent.remember(
        "Notebook note: người dùng quan tâm nhiều đến AI agents, retrieval, RAG "
        "và muốn học theo hướng application thực chiến.",
        user_id=user_id,
    )


def main() -> None:
    agent = HybridMemoryAgent()
    user_id = "u_001"
    seed_memories(agent, user_id)

    warm_up_queries = [
        "Mình muốn học thêm về cloud security roadmap",
        "Có tài liệu nào về RAG và agent không",
    ]
    for query in warm_up_queries:
        agent.recall(query, user_id=user_id)

    queries = [
        "Tôi đã đọc gì về Kubernetes?",
        "Recommend đọc gì tiếp",
        "Tôi đang quan tâm gì gần đây?",
        "Tài liệu về tự động mở rộng hạ tầng?",
        "Cho tôi summary cloud security",
    ]

    for i, query in enumerate(queries, start=1):
        print(f"\n=== Query {i}: {query} ===")
        print(agent.recall(query, user_id=user_id))


if __name__ == "__main__":
    main()
