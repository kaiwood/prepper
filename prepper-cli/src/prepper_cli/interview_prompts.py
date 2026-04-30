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
        "Use realistic implementation challenges with moderate ambiguity. "
        "Avoid open-ended architecture, distributed systems, or concurrency-heavy designs unless they are narrowly scoped. "
        "Expect strong trade-off reasoning, robust edge-case handling, and clear communication. "
        "Provide limited framing hints when they help the candidate make a precise answer."
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


def _interview_stage_family(descriptor: PromptDescriptor) -> str:
    prompt_identity = f"{descriptor.id} {descriptor.name}".casefold()
    if "behavior" in prompt_identity:
        return "behavioral"
    if "coding" in prompt_identity or "technical" in prompt_identity:
        return "coding"
    return "general"


def _select_stage_focus(stages: tuple[str, ...], question_count: int) -> str:
    stage_index = max(0, min(question_count, len(stages) - 1))
    return stages[stage_index]


def build_active_stage_instruction(
    descriptor: PromptDescriptor,
    question_count: int,
    question_limit: int,
) -> str:
    family = _interview_stage_family(descriptor)
    next_question_number = min(question_count + 1, question_limit)

    if family == "behavioral":
        stage_focus = _select_stage_focus(
            (
                "establish the STAR situation, task, and intended outcome",
                "force concrete ownership, actions, and decisions with specific examples",
                "probe trade-offs, conflict, constraints, and decision rationale",
                "make the result measurable and connect it to stakeholders or business impact",
                "ask for reflection, lessons learned, or what they would do differently",
            ),
            question_count,
        )
        weak_answer_guidance = (
            "If the latest answer is vague, ask for a named decision, concrete action, "
            "measurable result, or exact stakeholder impact instead of moving to a new story. "
        )
    elif family == "coding":
        stage_focus = _select_stage_focus(
            (
                "present a scoped implementation problem with concrete inputs, outputs, constraints, and one example",
                "probe one edge case with a manageable trace and ask for the next exact state change",
                "ask for pseudocode for one important operation or branch, plus its complexity",
                "check one correctness invariant or one missing edge case from the candidate's last answer",
                "use the final active question for one technical proof, edge case, or complexity guarantee still missing",
            ),
            question_count,
        )
        weak_answer_guidance = (
            "If the latest answer is vague or hedged, briefly frame the missing concept, then ask for exact pseudocode, a worked trace, "
            "a correctness invariant, or the precise state stored before broad trade-offs. "
            "A framing hint may name one viable structure or convention, but must not solve the whole problem. "
            "Do not leave exact formulas, index arithmetic, or complexity analysis until the final active question. "
        )
    else:
        stage_focus = _select_stage_focus(
            (
                "establish the candidate's approach and key assumptions",
                "probe missing details, constraints, and edge cases",
                "ask for concrete steps and decision rationale",
                "challenge trade-offs, correctness, and measurable impact",
                "ask for reflection, alternatives, or lessons learned",
            ),
            question_count,
        )
        weak_answer_guidance = (
            "If the latest answer is vague, ask for one concrete example, exact next step, "
            "or decision rationale before changing topic. "
        )

    return (
        "\n\nActive interview stage guidance: "
        f"The next scored question is {next_question_number}/{question_limit}. "
        f"Stage focus: {stage_focus}. "
        "Use this focus as guidance, not as a script. "
        "Ground the next question in the candidate's latest answer and ask for the most important missing detail. "
        f"{weak_answer_guidance}"
        "Keep all numeric limits, examples, and assumptions consistent with the original problem statement. "
        "Ask one concise question, not a multi-part checklist or numbered list. "
        "If the previous answer missed your request, adapt by narrowing to the next smallest concrete step instead of repeating the same broad prompt. "
        "Do not repeat a prior interviewer question or restate the same fallback wording. "
        "Ask exactly one candidate-facing question."
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
        "Do not introduce or reintroduce yourself, and do not mention your name or title. "
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
    sections.append(
        build_active_stage_instruction(
            descriptor=descriptor,
            question_count=question_count,
            question_limit=question_limit,
        )
    )
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
