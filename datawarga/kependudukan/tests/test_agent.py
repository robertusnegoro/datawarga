import json
from django.test import TestCase

from ..ai.ai_service import BaseAIProvider
from ..ai.agent import SystemAdapter, AgentService, AgentConversation


class MockSystemAdapter(SystemAdapter):
    def __init__(self):
        self.warga_db = []
        self.kompleks_db = []
        self.iuran_db = []

    def search_warga(self, query: str) -> list[dict]:
        res = []
        for w in self.warga_db:
            if query.lower() in w["nama_lengkap"].lower() or query in w["nik"]:
                res.append(w)
        return res

    def get_warga_detail(self, warga_id: int) -> dict | None:
        for w in self.warga_db:
            if w["id"] == warga_id:
                return w
        return None

    def search_kompleks(self, query: str) -> list[dict]:
        res = []
        for k in self.kompleks_db:
            if (
                query.lower() in f"{k['blok']}/{k['nomor']}".lower()
                or query.lower() in k["blok"].lower()
            ):
                res.append(k)
        return res

    def get_kompleks_detail(self, kompleks_id: int) -> dict | None:
        for k in self.kompleks_db:
            if k["id"] == kompleks_id:
                # Mock residents list
                residents = [
                    w for w in self.warga_db if w.get("kompleks_id") == kompleks_id
                ]
                return {**k, "residents": residents}
        return None

    def check_iuran(self, blok_no: str, tahun: int) -> list[dict]:
        res = []
        for i in self.iuran_db:
            if i["blok_no"].lower() == blok_no.lower() and i["periode_tahun"] == tahun:
                res.append(i)
        return res

    def add_warga(self, data: dict) -> dict:
        new_id = len(self.warga_db) + 1
        new_warga = {
            "id": new_id,
            "nama_lengkap": data.get("nama_lengkap", ""),
            "nik": data.get("nik", ""),
            "jenis_kelamin": data.get("jenis_kelamin", "PEREMPUAN"),
            "agama": data.get("agama", ""),
            "tempat_lahir": data.get("tempat_lahir", ""),
            "tanggal_lahir": data.get("tanggal_lahir"),
            "no_kk": data.get("no_kk", ""),
            "no_hp": data.get("no_hp", ""),
            "status_tinggal": data.get("status_tinggal", "TETAP"),
            "status_keluarga": data.get("status_keluarga", "N/A"),
            "kompleks_id": data.get("kompleks_id"),
            "kepala_keluarga": bool(data.get("kepala_keluarga", False)),
            "alamat": f"Blok ID {data.get('kompleks_id')}"
            if data.get("kompleks_id")
            else "Tidak ada alamat",
        }
        self.warga_db.append(new_warga)
        return new_warga

    def update_warga(self, warga_id: int, updates: dict) -> dict:
        for w in self.warga_db:
            if w["id"] == warga_id:
                w.update(updates)
                return w
        raise ValueError("Warga not found")


class MockAIProvider(BaseAIProvider):
    def __init__(self):
        self.responses = []
        self.call_count = 0

    def extract_ktp_data(self, image_bytes: bytes, correlation_id: str = None) -> dict:
        return {}

    def get_remaining_quota(self, correlation_id: str = None) -> float | None:
        return None

    def chat_completion(
        self,
        messages: list[dict],
        response_format: dict = None,
        correlation_id: str = None,
    ) -> str:
        if self.call_count < len(self.responses):
            resp = self.responses[self.call_count]
            self.call_count += 1
            return resp
        return json.dumps(
            {"thought": "default", "tool_call": None, "reply": "Default response"}
        )


class AgentTestCase(TestCase):
    def setUp(self):
        self.adapter = MockSystemAdapter()
        self.adapter.warga_db = [
            {
                "id": 1,
                "nama_lengkap": "Budi Santoso",
                "nik": "1234567890123456",
                "no_kk": "3201234567890123",
                "alamat": "Blok J2/5",
                "kompleks_id": 5,
                "status_tinggal": "TETAP",
                "status_keluarga": "SUAMI",
            }
        ]
        self.adapter.kompleks_db = [
            {
                "id": 5,
                "blok": "J2",
                "nomor": "5",
                "cluster": "Sektor 1",
                "rt": "01",
                "rw": "02",
            }
        ]
        self.adapter.iuran_db = [
            {
                "blok_no": "J2/5",
                "periode_bulan": 1,
                "periode_bulan_name": "Januari",
                "periode_tahun": 2026,
                "total_bayar": 50000,
                "keterangan": "Lunas",
            }
        ]
        self.ai = MockAIProvider()
        self.agent = AgentService(self.ai)

    def test_out_of_scope_query(self):
        # Setup mock behavior to reply with a refusal as requested by prompt rules
        refusal_json = json.dumps(
            {
                "thought": "The user is asking for a recipe. This is outside the scope of the DataWarga system.",
                "tool_call": None,
                "reply": "Maaf, saya hanya dapat membantu Anda dengan tugas-tugas sistem DataWarga seperti mencari warga, mengecek iuran, atau mendaftarkan warga baru.",
            }
        )
        self.ai.responses = [refusal_json]

        conv = AgentConversation(user_id=123)
        conv.add_user_message("Bagaimana cara memasak nasi goreng?")

        reply = self.agent.run_agent_turn(conv.messages, self.adapter)
        self.assertIn(
            "hanya dapat membantu Anda dengan tugas-tugas sistem DataWarga", reply
        )
        self.assertEqual(self.ai.call_count, 1)

    def test_search_warga_tool_flow(self):
        # Turn 1: Agent decides to call the search tool
        tool_call_json = json.dumps(
            {
                "thought": "I need to search for a resident named Budi.",
                "tool_call": {"name": "search_warga", "arguments": {"query": "Budi"}},
                "reply": "Mencari data warga bernama Budi...",
            }
        )
        # Turn 2: Agent receives the tool output and summarizes it
        summary_json = json.dumps(
            {
                "thought": "The search returned Budi Santoso. I will present the details to the user.",
                "tool_call": None,
                "reply": "Saya menemukan warga bernama Budi Santoso (NIK: 1234567890123456) tinggal di Blok J2/5.",
            }
        )

        self.ai.responses = [tool_call_json, summary_json]

        conv = AgentConversation(user_id=123)
        conv.add_user_message("Cari warga bernama Budi")

        reply = self.agent.run_agent_turn(conv.messages, self.adapter)
        self.assertEqual(
            reply,
            "Saya menemukan warga bernama Budi Santoso (NIK: 1234567890123456) tinggal di Blok J2/5.",
        )
        self.assertEqual(self.ai.call_count, 2)

    def test_check_iuran_tool_flow(self):
        tool_call_json = json.dumps(
            {
                "thought": "I need to check the dues for house J2/5 in year 2026.",
                "tool_call": {
                    "name": "check_iuran",
                    "arguments": {"blok_no": "J2/5", "tahun": 2026},
                },
                "reply": "Mengecek iuran Blok J2/5...",
            }
        )
        summary_json = json.dumps(
            {
                "thought": "Iuran check returned 1 payment for Januari. I will summarize it.",
                "tool_call": None,
                "reply": "Untuk Blok J2/5 tahun 2026, iuran yang tercatat adalah: Bulan Januari: Lunas (Rp 50.000).",
            }
        )

        self.ai.responses = [tool_call_json, summary_json]

        conv = AgentConversation(user_id=123)
        conv.add_user_message("Cek iuran J2/5 tahun 2026")

        reply = self.agent.run_agent_turn(conv.messages, self.adapter)
        self.assertIn("Bulan Januari: Lunas", reply)
        self.assertEqual(self.ai.call_count, 2)

    def test_add_warga_tool_flow(self):
        tool_call_json = json.dumps(
            {
                "thought": "User has provided details for adding a citizen.",
                "tool_call": {
                    "name": "add_warga",
                    "arguments": {
                        "nama_lengkap": "John Doe",
                        "nik": "9876543210123456",
                        "jenis_kelamin": "LAKI-LAKI",
                        "agama": "KRISTEN",
                        "tempat_lahir": "Surabaya",
                        "tanggal_lahir": "1992-05-15",
                        "kompleks_id": 5,
                    },
                },
                "reply": "Menambahkan warga...",
            }
        )
        summary_json = json.dumps(
            {
                "thought": "Warga successfully added.",
                "tool_call": None,
                "reply": "Warga baru bernama John Doe (NIK: 9876543210123456) berhasil ditambahkan ke Blok ID 5.",
            }
        )

        self.ai.responses = [tool_call_json, summary_json]

        conv = AgentConversation(user_id=123)
        conv.add_user_message(
            "Tolong daftarkan warga baru John Doe, NIK 9876543210123456, Kristen, Laki-laki, lahir di Surabaya 1992-05-15, tinggal di rumah kompleks id 5."
        )

        reply = self.agent.run_agent_turn(conv.messages, self.adapter)
        self.assertIn("berhasil ditambahkan", reply)
        self.assertEqual(len(self.adapter.warga_db), 2)
        self.assertEqual(self.adapter.warga_db[1]["nama_lengkap"], "John Doe")
        self.assertEqual(self.ai.call_count, 2)
