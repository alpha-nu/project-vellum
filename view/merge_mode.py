from enum import Enum


class MergeMode(Enum):
    NO_MERGE = "no_merge"
    MERGE = "merge"
    PER_PAGE = "per_page"

    @property
    def display_name(self) -> str:
        return {
            MergeMode.NO_MERGE: "no merge",
            MergeMode.MERGE: "merge",
            MergeMode.PER_PAGE: "file per page"
        }[self]

    @property
    def display_hint(self) -> str:
        return {
            MergeMode.NO_MERGE: "(separate file per document)",
            MergeMode.MERGE: "(combine all into single file)",
            MergeMode.PER_PAGE: "(one file per page/chapter)"
        }[self]