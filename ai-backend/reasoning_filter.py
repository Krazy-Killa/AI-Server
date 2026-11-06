"""Filter model reasoning blocks from assistant-visible text."""

from __future__ import annotations


class ReasoningFilter:
    """Remove <think> blocks while retaining safe text across stream chunks."""

    _OPEN_TAG = "<think>"
    _CLOSE_TAG = "</think>"
    _TAGS = (_OPEN_TAG, _CLOSE_TAG)

    def __init__(self) -> None:
        self._buffer = ""
        self._depth = 0

    @classmethod
    def _partial_tag_suffix_length(cls, text: str) -> int:
        lowered = text.lower()
        return max(
            (
                length
                for tag in cls._TAGS
                for length in range(1, min(len(lowered), len(tag) - 1) + 1)
                if lowered.endswith(tag[:length])
            ),
            default=0,
        )

    def feed(self, chunk: str) -> str:
        self._buffer += chunk
        visible: list[str] = []

        while self._buffer:
            lowered = self._buffer.lower()
            open_index = lowered.find(self._OPEN_TAG)
            close_index = lowered.find(self._CLOSE_TAG)

            if self._depth:
                if open_index == -1 and close_index == -1:
                    keep = self._partial_tag_suffix_length(self._buffer)
                    self._buffer = self._buffer[-keep:] if keep else ""
                    break
                if open_index != -1 and (close_index == -1 or open_index < close_index):
                    self._buffer = self._buffer[open_index + len(self._OPEN_TAG) :]
                    self._depth += 1
                else:
                    self._buffer = self._buffer[close_index + len(self._CLOSE_TAG) :]
                    self._depth -= 1
                continue

            if close_index != -1 and (open_index == -1 or close_index < open_index):
                visible.append(self._buffer[:close_index])
                self._buffer = self._buffer[close_index + len(self._CLOSE_TAG) :]
                continue
            if open_index != -1:
                visible.append(self._buffer[:open_index])
                self._buffer = self._buffer[open_index + len(self._OPEN_TAG) :]
                self._depth = 1
                continue

            keep = self._partial_tag_suffix_length(self._buffer)
            if keep:
                visible.append(self._buffer[:-keep])
                self._buffer = self._buffer[-keep:]
            else:
                visible.append(self._buffer)
                self._buffer = ""
            break

        return "".join(visible)

    def finish(self) -> str:
        if self._depth:
            self._buffer = ""
            self._depth = 0
            return ""

        trailing = self._buffer
        keep = self._partial_tag_suffix_length(trailing)
        if keep:
            trailing = trailing[:-keep]
        self._buffer = ""
        return trailing


def strip_reasoning_blocks(text: str) -> str:
    reasoning_filter = ReasoningFilter()
    return reasoning_filter.feed(text) + reasoning_filter.finish()
