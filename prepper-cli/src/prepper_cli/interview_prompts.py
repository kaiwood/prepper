from .system_prompts import PromptDescriptor

METADATA_PREFIX = "[PREPPER_JSON]"


def build_difficulty_instruction(difficulty: str) -> str:
    if difficulty == "easy":
        return (
            "\n\nDifficulty mode: Junior-level (easy). "
            "Favor practical, well-scoped coding problems with lower ambiguity. "
            "Offer concise hints when the candidate is clearly stuck. "
            "Keep follow-ups implementation-focused and moderate in depth."
        )

    if difficulty == "hard":
        return (
            "\n\nDifficulty mode: Principal-level (hard). "
            "Use more ambiguous, open-ended problems and probe system-level trade-offs. "
            "Push deeper follow-ups on architecture, scaling, reliability, and constraints. "
            "Keep hints minimal unless explicitly requested."
        )

    return (
        "\n\nDifficulty mode: Senior-level (medium). "
        "Use realistic production-oriented coding challenges with moderate ambiguity. "
        "Expect strong trade-off reasoning, robust edge-case handling, and clear communication. "
        "Provide limited hints only when appropriate."
    )


def build_metadata_contract_instruction() -> str:
    return (
        "\n\nResponse format requirement: End EVERY interviewer reply with a single metadata suffix "
        f"line in this exact format: {METADATA_PREFIX} {{\"turn_type\":\"QUESTION|OTHER\",\"interview_complete\":true|false}}. "
        "Do not add extra keys. Keep metadata valid JSON on a single line."
    )


def build_runtime_interview_instruction(
    question_count: int,
    question_limit: int,
) -> str:
    if question_count >= question_limit:
        return (
            "\n\nRuntime rule: You already asked the configured number of scored interview "
            "questions. Do not ask another new question. Provide a concise closing response, "
            "state that the interview is now over, and thank the candidate. "
            "Set interview_complete to true in your metadata."
        )

    remaining = question_limit - question_count
    return (
        "\n\nRuntime rule: You are still in active interview mode. "
        f"Scored interview questions asked so far: {question_count}/{question_limit}. "
        f"Remaining scored questions: {remaining}. Ask at most one new focused question in this turn. "
        "Clarifications are allowed but should be concise. "
        "Do not close the interview, do not say the interview is over, and do not thank the candidate for their time. "
        "Set interview_complete to false. "
        "Only the runtime override after the configured question limit may end the interview. "
        "Do not call a question final unless it is the last remaining scored question."
    )


def build_forced_closing_instruction(
    question_count: int,
    question_limit: int,
) -> str:
    return (
        "\n\nRuntime override: The interview must end now because the scored question "
        f"roundtrip limit has been reached ({question_count}/{question_limit}). "
        "Do not ask any new question. Provide a brief closing statement that clearly says "
        "the interview is now over and thanks the candidate. "
        "End with metadata using turn_type OTHER and interview_complete true."
    )


def build_prompt_with_difficulty(
    descriptor: PromptDescriptor,
    difficulty: str | None,
) -> str:
    sections = [descriptor.content]
    if difficulty is not None:
        sections.append(build_difficulty_instruction(difficulty))
    return "".join(sections)


def build_interview_opener_system_prompt(
    descriptor: PromptDescriptor,
    difficulty: str | None,
) -> str:
    return build_prompt_with_difficulty(descriptor, difficulty)


def build_active_interview_system_prompt(
    descriptor: PromptDescriptor,
    difficulty: str | None,
    question_count: int,
    question_limit: int,
) -> str:
    sections = [
        descriptor.content,
        build_metadata_contract_instruction(),
    ]
    if difficulty is not None:
        sections.append(build_difficulty_instruction(difficulty))
    sections.append(build_runtime_interview_instruction(question_count, question_limit))
    return "".join(sections)


def build_forced_closing_system_prompt(
    descriptor: PromptDescriptor,
    difficulty: str | None,
    question_count: int,
    question_limit: int,
) -> str:
    sections = [
        descriptor.content,
        build_metadata_contract_instruction(),
    ]
    if difficulty is not None:
        sections.append(build_difficulty_instruction(difficulty))
    sections.append(build_forced_closing_instruction(question_count, question_limit))
    return "".join(sections)
