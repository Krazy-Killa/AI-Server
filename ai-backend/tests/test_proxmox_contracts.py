import unittest

from proxmox_contracts import (
    PROXMOX_INVENTORY_CONTRACT,
    GameServerProposal,
    NetworkServiceProposal,
    ProxmoxGuestReference,
    ProxmoxVMActionProposal,
)


class ProxmoxContractsTests(unittest.TestCase):
    def test_inventory_contract_is_read_only_and_least_privilege(self):
        self.assertEqual(PROXMOX_INVENTORY_CONTRACT.method, "GET")
        self.assertEqual(
            PROXMOX_INVENTORY_CONTRACT.path,
            "/api2/json/cluster/resources?type=vm",
        )
        self.assertEqual(
            PROXMOX_INVENTORY_CONTRACT.required_privileges,
            ("Sys.Audit", "VM.Audit"),
        )
        self.assertNotIn("execute", PROXMOX_INVENTORY_CONTRACT.returned_fields)
        self.assertIn("power", PROXMOX_INVENTORY_CONTRACT.forbidden_capabilities)

    def test_vm_lifecycle_intent_is_admin_confirmed_and_proposal_only(self):
        guest = ProxmoxGuestReference(node="pve", vmid=100)
        with self.assertRaisesRegex(ValueError, "admin role"):
            ProxmoxVMActionProposal(
                operation="start",
                guest=guest,
                requested_by_role="operator",
                confirmation="PROPOSE VM 100 START",
            )

        proposal = ProxmoxVMActionProposal(
            operation="start",
            guest=guest,
            requested_by_role="admin",
            confirmation="PROPOSE VM 100 START",
        )
        self.assertEqual(proposal.execution_mode, "proposal_only")

    def test_vm_lifecycle_proposal_requires_exact_confirmation(self):
        with self.assertRaisesRegex(ValueError, "explicit confirmation"):
            ProxmoxVMActionProposal(
                operation="stop",
                guest=ProxmoxGuestReference(node="pve", vmid=100),
                requested_by_role="admin",
                confirmation="yes",
            )

    def test_network_inspection_is_readable_but_mutations_are_admin_confirmed(self):
        inspection = NetworkServiceProposal(
            service="dns",
            operation="inspect",
            scope="lab subnet",
            requested_by_role="viewer",
        )
        self.assertEqual(inspection.execution_mode, "proposal_only")

        with self.assertRaisesRegex(ValueError, "admin role"):
            NetworkServiceProposal(
                service="routing_firewall",
                operation="configure",
                scope="lab subnet",
                requested_by_role="operator",
                confirmation="PROPOSE CONFIGURE ROUTING_FIREWALL",
            )

    def test_game_server_restore_is_confirmed_admin_proposal_only(self):
        proposal = GameServerProposal(
            instance_id="family-minecraft",
            operation="restore",
            requested_by_role="admin",
            confirmation=(
                "PROPOSE RESTORE GAME SERVER family-minecraft"
            ),
        )
        self.assertEqual(proposal.execution_mode, "proposal_only")

        with self.assertRaisesRegex(ValueError, "explicit confirmation"):
            GameServerProposal(
                instance_id="family-minecraft",
                operation="restore",
                requested_by_role="admin",
            )

    def test_invalid_guest_reference_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "positive integer"):
            ProxmoxGuestReference(node="pve", vmid=True)


if __name__ == "__main__":
    unittest.main()
