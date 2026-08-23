"""Pure-Python checks for the Yefira ↔ MoziToolKit attribute boundary."""

from pathlib import Path
import importlib.util
import unittest


ATTRIBUTES_PATH = Path(__file__).resolve().parent.parent / "dcc_plugins" / "yefira_blender" / "core" / "attributes.py"
spec = importlib.util.spec_from_file_location("yefira_attribute_contract", ATTRIBUTES_PATH)
attributes = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(attributes)


class TestAttributeContract(unittest.TestCase):
    def test_private_fields_are_yefira_namespaced(self):
        private_fields = (
            attributes.BLOCK_TYPE, attributes.TEMPLATE_INDEX,
            attributes.INSTANCE_ROTATION, attributes.BLOCK_CENTER,
            attributes.MC_POSITION, attributes.BLOCK_STATE, attributes.BLOCK_KEY,
            attributes.CUBE_FACE_NORMAL, attributes.LOCAL_FACE_ID, attributes.LOCAL_UV,
        )
        self.assertTrue(all(name.startswith("yefira_") for name in private_fields))

    def test_mtk_contract_is_not_shadowed_by_legacy_duplicates(self):
        self.assertIn(attributes.MTK_IS_OPAQUE, attributes.POINT_ATTRIBUTE_NAMES)
        self.assertNotIn("is_opaque", attributes.POINT_ATTRIBUTE_NAMES)
        self.assertIn("is_opaque", attributes.LEGACY_POINT_ATTRIBUTE_NAMES)
        self.assertNotIn("instance_offset", attributes.POINT_ATTRIBUTE_NAMES)

    def test_per_face_contract_is_complete(self):
        self.assertEqual(len(attributes.FACES), 6)
        self.assertEqual(len(attributes.FACE_TILE_ATTRIBUTES), 6)
        self.assertEqual(len(attributes.FACE_ANIM_FRAME_SIZE_ATTRIBUTES), 6)
        self.assertEqual(
            attributes.face_attribute("tile", "north"), "mtk_tile_north",
        )

    def test_instance_transfer_includes_biome_tint_color(self):
        transfer_attrs = [attr for attr, _ in attributes.INSTANCE_TRANSFER_SPECS]
        self.assertIn(attributes.MTK_BIOME_TINT_COLOR, transfer_attrs)


if __name__ == "__main__":
    unittest.main(argv=['first-arg-is-ignored'])
