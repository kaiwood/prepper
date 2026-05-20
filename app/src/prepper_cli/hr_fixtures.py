from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REQUIRED_FIXTURE_FILES = ("company.md", "role.md", "resume.md", "profile.md")
REQUIRED_TRANSCRIPT_FILES = ("transcripts/strong.md", "transcripts/weak.md")
_ALLOWED_TRANSCRIPT_SECTIONS = {
    "Interviewer",
    "Candidate",
    "Tool Event",
    "Source",
    "Expected Final Result",
}
_TURN_SECTIONS = {"Interviewer": "interviewer", "Candidate": "candidate"}


@dataclass(frozen=True)
class TranscriptTurn:
    role: str
    content: str


@dataclass(frozen=True)
class TranscriptToolEvent:
    tool_name: str
    data: dict[str, str]


@dataclass(frozen=True)
class TranscriptSource:
    title: str
    url: str
    excerpt: str


@dataclass(frozen=True)
class ExpectedFinalResult:
    overall_score: float
    passed: bool
    strengths: tuple[str, ...]
    improvements: tuple[str, ...]


@dataclass(frozen=True)
class Transcript:
    fixture_id: str
    candidate: str
    turns: tuple[TranscriptTurn, ...]
    tool_events: tuple[TranscriptToolEvent, ...]
    sources: tuple[TranscriptSource, ...]
    expected_final_result: ExpectedFinalResult
    metadata: dict[str, str]


@dataclass(frozen=True)
class HrFixture:
    id: str
    path: Path
    company_markdown: str
    role_markdown: str
    resume_markdown: str
    profile_markdown: str
    transcripts: dict[str, Transcript]


class FixtureValidationError(ValueError):
    """Raised when an HR fixture or transcript is malformed."""


def get_hr_fixture_root(root: Path | str | None = None) -> Path:
    if root is not None:
        return Path(root)

    env_root = os.environ.get("PREPPER_HR_FIXTURE_ROOT")
    if env_root:
        return Path(env_root)

    app_dir = Path(__file__).resolve().parents[2]
    candidates = (
        app_dir / "fixtures" / "hr",
        Path.cwd() / "fixtures" / "hr",
        Path.cwd() / "app" / "fixtures" / "hr",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def list_hr_fixture_ids(root: Path | str | None = None) -> list[str]:
    fixture_root = get_hr_fixture_root(root)
    if not fixture_root.exists():
        return []

    return sorted(
        path.name
        for path in fixture_root.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    )


def load_hr_fixture(fixture_id: str, root: Path | str | None = None) -> HrFixture:
    return validate_hr_fixture(fixture_id, root=root)


def validate_hr_fixture(fixture_id: str, root: Path | str | None = None) -> HrFixture:
    fixture_path = _resolve_fixture_path(fixture_id, root)
    if not fixture_path.exists() or not fixture_path.is_dir():
        raise FixtureValidationError(f"HR fixture '{fixture_id}' was not found")

    missing_paths = [
        relative_path
        for relative_path in (*REQUIRED_FIXTURE_FILES, *REQUIRED_TRANSCRIPT_FILES)
        if not (fixture_path / relative_path).is_file()
    ]
    if missing_paths:
        missing_text = ", ".join(missing_paths)
        raise FixtureValidationError(
            f"HR fixture '{fixture_id}' is missing required file(s): {missing_text}"
        )

    transcripts: dict[str, Transcript] = {}
    for relative_path in REQUIRED_TRANSCRIPT_FILES:
        transcript_path = fixture_path / relative_path
        transcript = parse_transcript_file(transcript_path)
        expected_candidate = transcript_path.stem
        if transcript.fixture_id != fixture_id:
            raise FixtureValidationError(
                f"Transcript '{relative_path}' declares fixture '{transcript.fixture_id}', expected '{fixture_id}'"
            )
        if transcript.candidate != expected_candidate:
            raise FixtureValidationError(
                f"Transcript '{relative_path}' declares candidate '{transcript.candidate}', expected '{expected_candidate}'"
            )
        transcripts[expected_candidate] = transcript

    return HrFixture(
        id=fixture_id,
        path=fixture_path,
        company_markdown=(fixture_path / "company.md").read_text(encoding="utf-8"),
        role_markdown=(fixture_path / "role.md").read_text(encoding="utf-8"),
        resume_markdown=(fixture_path / "resume.md").read_text(encoding="utf-8"),
        profile_markdown=(fixture_path / "profile.md").read_text(encoding="utf-8"),
        transcripts=transcripts,
    )


def parse_transcript_file(path: Path | str) -> Transcript:
    transcript_path = Path(path)
    return parse_transcript_markdown(
        transcript_path.read_text(encoding="utf-8"),
        source_name=str(transcript_path),
    )


def parse_transcript_markdown(raw: str, *, source_name: str = "<transcript>") -> Transcript:
    metadata, body_lines = _split_front_matter(raw, source_name)
    fixture_id = _require_metadata(metadata, "fixture", source_name)
    candidate = _require_metadata(metadata, "candidate", source_name)

    sections = _parse_sections(body_lines, source_name)

    turns: list[TranscriptTurn] = []
    tool_events: list[TranscriptToolEvent] = []
    sources: list[TranscriptSource] = []
    expected_final_result: ExpectedFinalResult | None = None

    for heading, section_lines in sections:
        if heading in _TURN_SECTIONS:
            content = "\n".join(section_lines).strip()
            if not content:
                raise FixtureValidationError(
                    f"Transcript '{source_name}' has an empty {heading} turn"
                )
            turns.append(TranscriptTurn(role=_TURN_SECTIONS[heading], content=content))
        elif heading == "Tool Event":
            data = _parse_key_value_block(section_lines, source_name, heading)
            tool_name = data.get("tool", "").strip()
            if not tool_name:
                raise FixtureValidationError(
                    f"Transcript '{source_name}' has a Tool Event without 'tool'"
                )
            tool_events.append(
                TranscriptToolEvent(
                    tool_name=tool_name,
                    data={key: value for key, value in data.items() if key != "tool"},
                )
            )
        elif heading == "Source":
            data = _parse_key_value_block(section_lines, source_name, heading)
            sources.append(
                TranscriptSource(
                    title=_require_block_value(data, "title", source_name, heading),
                    url=_require_block_value(data, "url", source_name, heading),
                    excerpt=_require_block_value(data, "excerpt", source_name, heading),
                )
            )
        elif heading == "Expected Final Result":
            if expected_final_result is not None:
                raise FixtureValidationError(
                    f"Transcript '{source_name}' contains multiple Expected Final Result sections"
                )
            expected_final_result = _parse_expected_final_result(
                section_lines, source_name
            )

    _validate_turns(turns, source_name)
    if expected_final_result is None:
        raise FixtureValidationError(
            f"Transcript '{source_name}' must include an Expected Final Result section"
        )
    if not tool_events:
        raise FixtureValidationError(
            f"Transcript '{source_name}' must include at least one Tool Event section"
        )
    if not sources:
        raise FixtureValidationError(
            f"Transcript '{source_name}' must include at least one Source section"
        )

    return Transcript(
        fixture_id=fixture_id,
        candidate=candidate,
        turns=tuple(turns),
        tool_events=tuple(tool_events),
        sources=tuple(sources),
        expected_final_result=expected_final_result,
        metadata=metadata,
    )


def _resolve_fixture_path(fixture_id: str, root: Path | str | None) -> Path:
    normalized_id = fixture_id.strip()
    if not normalized_id:
        raise FixtureValidationError("HR fixture id is required")
    if Path(normalized_id).name != normalized_id or normalized_id in {".", ".."}:
        raise FixtureValidationError(f"Invalid HR fixture id '{fixture_id}'")
    return get_hr_fixture_root(root) / normalized_id


def _split_front_matter(raw: str, source_name: str) -> tuple[dict[str, str], list[str]]:
    lines = raw.splitlines()
    if not lines or lines[0].strip() != "---":
        raise FixtureValidationError(
            f"Transcript '{source_name}' must start with front matter delimited by ---"
        )

    closing_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            closing_index = index
            break
    if closing_index is None:
        raise FixtureValidationError(
            f"Transcript '{source_name}' has unterminated front matter"
        )

    metadata = _parse_key_value_block(
        lines[1:closing_index], source_name, "front matter"
    )
    return metadata, lines[closing_index + 1 :]


def _parse_sections(
    body_lines: Iterable[str], source_name: str
) -> list[tuple[str, list[str]]]:
    sections: list[tuple[str, list[str]]] = []
    current_heading: str | None = None
    current_lines: list[str] = []

    for line_number, line in enumerate(body_lines, start=1):
        if line.startswith("## "):
            if current_heading is not None:
                sections.append((current_heading, current_lines))
            current_heading = line[3:].strip()
            if current_heading not in _ALLOWED_TRANSCRIPT_SECTIONS:
                allowed = ", ".join(sorted(_ALLOWED_TRANSCRIPT_SECTIONS))
                raise FixtureValidationError(
                    f"Transcript '{source_name}' has unknown section '{current_heading}' near body line {line_number}. Allowed: {allowed}"
                )
            current_lines = []
            continue

        if current_heading is None:
            if line.strip():
                raise FixtureValidationError(
                    f"Transcript '{source_name}' has content before the first section heading"
                )
            continue

        current_lines.append(line)

    if current_heading is not None:
        sections.append((current_heading, current_lines))

    if not sections:
        raise FixtureValidationError(
            f"Transcript '{source_name}' must contain Markdown sections"
        )

    return sections


def _parse_key_value_block(
    lines: Iterable[str], source_name: str, block_name: str
) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if ":" not in stripped:
            raise FixtureValidationError(
                f"Transcript '{source_name}' has malformed {block_name} line: {stripped}"
            )
        key, _, value = stripped.partition(":")
        normalized_key = key.strip()
        if not normalized_key:
            raise FixtureValidationError(
                f"Transcript '{source_name}' has an empty key in {block_name}"
            )
        data[normalized_key] = value.strip()
    return data


def _require_metadata(metadata: dict[str, str], key: str, source_name: str) -> str:
    value = metadata.get(key, "").strip()
    if not value:
        raise FixtureValidationError(
            f"Transcript '{source_name}' front matter is missing '{key}'"
        )
    return value


def _require_block_value(
    data: dict[str, str], key: str, source_name: str, block_name: str
) -> str:
    value = data.get(key, "").strip()
    if not value:
        raise FixtureValidationError(
            f"Transcript '{source_name}' {block_name} section is missing '{key}'"
        )
    return value


def _parse_expected_final_result(
    lines: Iterable[str], source_name: str
) -> ExpectedFinalResult:
    data = _parse_key_value_block(lines, source_name, "Expected Final Result")
    score_text = _require_block_value(
        data, "overall_score", source_name, "Expected Final Result"
    )
    try:
        overall_score = float(score_text)
    except ValueError as exc:
        raise FixtureValidationError(
            f"Transcript '{source_name}' Expected Final Result overall_score must be a number"
        ) from exc

    return ExpectedFinalResult(
        overall_score=overall_score,
        passed=_parse_bool(
            _require_block_value(data, "passed", source_name, "Expected Final Result"),
            source_name,
            "Expected Final Result passed",
        ),
        strengths=_parse_list(
            _require_block_value(data, "strengths", source_name, "Expected Final Result")
        ),
        improvements=_parse_list(
            _require_block_value(
                data, "improvements", source_name, "Expected Final Result"
            )
        ),
    )


def _parse_bool(value: str, source_name: str, field_name: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "yes", "1"}:
        return True
    if normalized in {"false", "no", "0"}:
        return False
    raise FixtureValidationError(
        f"Transcript '{source_name}' {field_name} must be true or false"
    )


def _parse_list(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split("|") if item.strip())


def _validate_turns(turns: list[TranscriptTurn], source_name: str) -> None:
    if not turns:
        raise FixtureValidationError(
            f"Transcript '{source_name}' must include interviewer and candidate turns"
        )
    if turns[0].role != "interviewer":
        raise FixtureValidationError(
            f"Transcript '{source_name}' first turn must be an Interviewer section"
        )
    if not any(turn.role == "candidate" for turn in turns):
        raise FixtureValidationError(
            f"Transcript '{source_name}' must include at least one Candidate section"
        )

    for previous, current in zip(turns, turns[1:]):
        if previous.role == current.role:
            raise FixtureValidationError(
                f"Transcript '{source_name}' interviewer and candidate turns must alternate"
            )
