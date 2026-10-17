import unittest

from diagnostic_knowledge import get_runbook, list_runbooks, search_runbooks


class DiagnosticKnowledgeTests(unittest.TestCase):
    def test_bundled_runbooks_are_reviewed_and_versioned(self):
        runbooks = list_runbooks()
        self.assertGreaterEqual(len(runbooks), 4)
        self.assertTrue(all(item.review_state == "reviewed" for item in runbooks))
        self.assertTrue(all(item.version for item in runbooks))
        self.assertTrue(all(item.owner and item.last_reviewed for item in runbooks))
        self.assertTrue(all(item.source == "built-in" for item in runbooks))
        self.assertEqual(len({item.id for item in runbooks}), len(runbooks))

    def test_platform_and_signal_filters_exclude_inapplicable_runbooks(self):
        pve_runbooks = list_runbooks(platform="proxmox-ve")
        self.assertTrue(pve_runbooks)
        self.assertTrue(
            all("proxmox-ve" in item.platforms for item in pve_runbooks)
        )

        matches = list_runbooks(
            platform="proxmox-ve",
            signal="proxmox.inventory.forbidden",
        )
        self.assertEqual([item.id for item in matches], ["RB-PVE-INVENTORY-002"])

    def test_search_is_local_deterministic_and_ranked(self):
        first = search_runbooks("Proxmox inventory 403 token ACL", platform="proxmox-ve")
        second = search_runbooks("Proxmox inventory 403 token ACL", platform="proxmox-ve")

        self.assertEqual(first, second)
        self.assertEqual(first[0].id, "RB-PVE-INVENTORY-002")
        self.assertNotIn(
            "RB-AI-DIAGNOSTICS-001",
            [runbook.id for runbook in first],
        )

    def test_empty_or_unmatched_search_returns_no_runbooks(self):
        self.assertEqual(search_runbooks("   "), ())
        self.assertEqual(search_runbooks("unrelated phrase"), ())

    def test_unknown_runbook_is_not_returned(self):
        self.assertIsNone(get_runbook("RB-UNKNOWN-999"))


if __name__ == "__main__":
    unittest.main()
