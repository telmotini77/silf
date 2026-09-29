import re


def test_carbonio_uid_metadata_pattern_matches_real_imap_responses():
    lines = [
        "OK [UIDVALIDITY 1] UIDs are valid for this mailbox",
        "OK [UIDNEXT 261] next expected UID is 261",
    ]

    values = {}
    for line in lines:
        for name in ("UIDVALIDITY", "UIDNEXT"):
            match = re.search(rf"{name}\s+(\d+)", line)
            if match:
                values[name] = int(match.group(1))

    assert values == {"UIDVALIDITY": 1, "UIDNEXT": 261}
