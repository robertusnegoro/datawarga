import abc
import json
import logging
from datetime import datetime
from django.db.models import Q
from kependudukan.ai.ai_service import BaseAIProvider

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are the DataWarga System Chat Agent, a specialized assistant for the DataWarga (Resident Directory and Payment) system.\n"
    "Your sole purpose is to help users manage residents (warga), houses (kompleks), and payments/dues (iuran).\n\n"
    "CRITICAL DIRECTIVE ON SCOPE:\n"
    "- You must ONLY answer questions and perform operations directly related to this system (DataWarga).\n"
    "- You MUST politely but firmly refuse all generic AI queries, such as requests for cooking recipes, coding consultation, writing essays, general knowledge, storytelling, translations, math help, or generic conversations.\n"
    "- If the request is out of scope, respond with a refusal message stating that you can only help with DataWarga system tasks.\n"
    "- NEVER execute any tools or write SQL if a query is out of scope.\n\n"
    "FORMAT REQUIREMENTS:\n"
    "You must respond ONLY with a raw JSON object. The JSON object must contain exactly three keys:\n"
    '1. "thought": A brief explanation of your reasoning or next step.\n'
    "2. \"tool_call\": A dictionary representing a tool to call, or null if no tool needs to be called. It must have 'name' and 'arguments' keys.\n"
    '3. "reply": The message to show to the user.\n\n'
    "Available tools:\n"
    '1. "search_warga" with argument "query" (str): Search for citizens by name, NIK, KK, complex/house block and number.\n'
    '2. "get_warga_detail" with argument "warga_id" (int): Retrieve detailed profile of a citizen.\n'
    '3. "search_kompleks" with argument "query" (str): Search for complex/house by block/number (e.g. "J2/5").\n'
    '4. "get_kompleks_detail" with argument "kompleks_id" (int): Retrieve details of a complex, including its resident list.\n'
    '5. "check_iuran" with arguments "blok_no" (str) and "tahun" (int): Check the payment history for a house in a specific year.\n'
    '6. "add_warga" with arguments:\n'
    '   - "nama_lengkap" (str)\n'
    '   - "nik" (str)\n'
    '   - "jenis_kelamin" (str - must be either "LAKI-LAKI" or "PEREMPUAN")\n'
    '   - "agama" (str - "ISLAM", "KATHOLIK", "KRISTEN", "HINDU", "BUDDHA", "KONGHUCU")\n'
    '   - "tempat_lahir" (str)\n'
    '   - "tanggal_lahir" (str - YYYY-MM-DD format)\n'
    '   - "no_kk" (str, optional)\n'
    '   - "no_hp" (str, optional)\n'
    '   - "status_tinggal" (str - "KONTRAK", "KOST", "TETAP", "PINDAH", "MENINGGAL", "LAINNYA", optional)\n'
    '   - "status_keluarga" (str - "SUAMI", "ISTRI", "ANAK", "ORANG TUA", "SAUDARA", "LAINNYA", "N/A", optional)\n'
    '   - "kompleks_id" (int, optional)\n'
    '   - "kepala_keluarga" (bool, optional)\n'
    '7. "update_warga" with arguments:\n'
    '   - "warga_id" (int)\n'
    '   - "updates" (dict containing fields to update, e.g. {"kompleks_id": 5})\n\n'
    "Rules for adding/updating:\n"
    "- If the user wants to add a new citizen, but some required fields (e.g., nama_lengkap, nik) are missing, ask for them.\n"
    "- If the user uploads a KTP, the system will automatically extract the fields and inject a SYSTEM message into your history. You should check the details, present them to the user, and ask for confirmation and house assignment."
)


class SystemAdapter(abc.ABC):
    @abc.abstractmethod
    def search_warga(self, query: str) -> list[dict]:
        pass

    @abc.abstractmethod
    def get_warga_detail(self, warga_id: int) -> dict | None:
        pass

    @abc.abstractmethod
    def search_kompleks(self, query: str) -> list[dict]:
        pass

    @abc.abstractmethod
    def get_kompleks_detail(self, kompleks_id: int) -> dict | None:
        pass

    @abc.abstractmethod
    def check_iuran(self, blok_no: str, tahun: int) -> list[dict]:
        pass

    @abc.abstractmethod
    def add_warga(self, data: dict) -> dict:
        pass

    @abc.abstractmethod
    def update_warga(self, warga_id: int, updates: dict) -> dict:
        pass


class DjangoSystemAdapter(SystemAdapter):
    def search_warga(self, query: str) -> list[dict]:
        from kependudukan.models import Warga

        query = query.strip()
        if "/" in query:
            parts = query.split("/")
            qs = Warga.objects.filter(
                kompleks__blok__icontains=parts[0].strip(),
                kompleks__nomor=parts[1].strip(),
            )
        else:
            qs = Warga.objects.filter(
                Q(nama_lengkap__icontains=query)
                | Q(nik__icontains=query)
                | Q(no_kk__icontains=query)
            )
        res = []
        for w in qs[:10]:
            res.append(
                {
                    "id": w.id,
                    "nama_lengkap": w.nama_lengkap,
                    "nik": w.nik,
                    "no_kk": w.no_kk,
                    "alamat": f"Blok {w.kompleks.blok}/{w.kompleks.nomor}"
                    if w.kompleks
                    else "Tidak ada alamat",
                    "status_tinggal": w.status_tinggal,
                    "status_keluarga": w.status_keluarga,
                }
            )
        return res

    def get_warga_detail(self, warga_id: int) -> dict | None:
        from kependudukan.models import Warga

        try:
            w = Warga.objects.get(pk=warga_id)
            return {
                "id": w.id,
                "nama_lengkap": w.nama_lengkap,
                "nik": w.nik,
                "no_kk": w.no_kk,
                "alamat": f"Blok {w.kompleks.blok}/{w.kompleks.nomor}"
                if w.kompleks
                else "Tidak ada alamat",
                "kompleks_id": w.kompleks.id if w.kompleks else None,
                "agama": w.agama,
                "email": w.email,
                "no_hp": w.no_hp,
                "pekerjaan": w.pekerjaan,
                "status": w.status,
                "tanggal_lahir": str(w.tanggal_lahir) if w.tanggal_lahir else None,
                "tempat_lahir": w.tempat_lahir,
                "jenis_kelamin": w.jenis_kelamin,
                "status_tinggal": w.status_tinggal,
                "status_keluarga": w.status_keluarga,
                "kepala_keluarga": w.kepala_keluarga,
            }
        except Warga.DoesNotExist:
            return None

    def search_kompleks(self, query: str) -> list[dict]:
        from kependudukan.models import Kompleks

        query = query.strip()
        if "/" in query:
            parts = query.split("/")
            qs = Kompleks.objects.filter(
                blok__icontains=parts[0].strip(), nomor=parts[1].strip()
            )
        else:
            qs = Kompleks.objects.filter(
                Q(blok__icontains=query)
                | Q(nomor__icontains=query)
                | Q(cluster__icontains=query)
            )
        res = []
        for k in qs[:10]:
            res.append(
                {
                    "id": k.id,
                    "blok": k.blok,
                    "nomor": k.nomor,
                    "cluster": k.cluster,
                    "rt": k.rt,
                    "rw": k.rw,
                    "alamat": f"Blok {k.blok}/{k.nomor}",
                }
            )
        return res

    def get_kompleks_detail(self, kompleks_id: int) -> dict | None:
        from kependudukan.models import Kompleks, Warga

        try:
            k = Kompleks.objects.get(pk=kompleks_id)
            residents = Warga.objects.filter(kompleks=k).exclude(
                status_tinggal__in=["PINDAH", "MENINGGAL"]
            )
            res_list = []
            for r in residents:
                res_list.append(
                    {
                        "id": r.id,
                        "nama_lengkap": r.nama_lengkap,
                        "status_keluarga": r.status_keluarga,
                        "kepala_keluarga": r.kepala_keluarga,
                    }
                )
            return {
                "id": k.id,
                "blok": k.blok,
                "nomor": k.nomor,
                "cluster": k.cluster,
                "rt": k.rt,
                "rw": k.rw,
                "residents": res_list,
            }
        except Kompleks.DoesNotExist:
            return None

    def check_iuran(self, blok_no: str, tahun: int) -> list[dict]:
        from kependudukan.models import Kompleks, TransaksiIuranBulanan

        if "/" not in blok_no:
            return []
        parts = blok_no.split("/")
        try:
            k = Kompleks.objects.get(
                blok__iexact=parts[0].strip(), nomor=parts[1].strip()
            )
            iurans = TransaksiIuranBulanan.objects.filter(
                kompleks=k, periode_tahun=tahun
            ).order_by("periode_bulan")
            res = []
            for i in iurans:
                month_name = "Bulan " + str(i.periode_bulan)
                for num, name in TransaksiIuranBulanan.LIST_BULAN:
                    if num == i.periode_bulan:
                        month_name = name
                        break
                res.append(
                    {
                        "periode_bulan": i.periode_bulan,
                        "periode_bulan_name": month_name,
                        "periode_tahun": i.periode_tahun,
                        "total_bayar": i.total_bayar,
                        "keterangan": i.keterangan,
                    }
                )
            return res
        except (Kompleks.DoesNotExist, ValueError):
            return []

    def add_warga(self, data: dict) -> dict:
        from kependudukan.models import Warga, Kompleks

        kompleks_obj = None
        kompleks_id = data.get("kompleks_id")
        if kompleks_id:
            try:
                kompleks_obj = Kompleks.objects.get(pk=kompleks_id)
            except (Kompleks.DoesNotExist, ValueError):
                pass

        tgl_lahir = None
        tgl_str = data.get("tanggal_lahir")
        if tgl_str:
            try:
                tgl_lahir = datetime.strptime(tgl_str, "%Y-%m-%d").date()
            except ValueError:
                pass

        w = Warga.objects.create(
            nama_lengkap=data.get("nama_lengkap", ""),
            nik=data.get("nik", ""),
            jenis_kelamin=data.get("jenis_kelamin", "PEREMPUAN"),
            agama=data.get("agama", ""),
            tempat_lahir=data.get("tempat_lahir", ""),
            tanggal_lahir=tgl_lahir,
            no_kk=data.get("no_kk", ""),
            no_hp=data.get("no_hp", ""),
            status_tinggal=data.get("status_tinggal", "TETAP"),
            status_keluarga=data.get("status_keluarga", "N/A"),
            kompleks=kompleks_obj,
            kepala_keluarga=bool(data.get("kepala_keluarga", False)),
        )
        return {
            "id": w.id,
            "nama_lengkap": w.nama_lengkap,
            "nik": w.nik,
            "alamat": f"Blok {w.kompleks.blok}/{w.kompleks.nomor}"
            if w.kompleks
            else "Tidak ada alamat",
        }

    def update_warga(self, warga_id: int, updates: dict) -> dict:
        from kependudukan.models import Warga, Kompleks

        w = Warga.objects.get(pk=warga_id)
        for k, v in updates.items():
            if k == "kompleks_id":
                if v:
                    w.kompleks = Kompleks.objects.get(pk=v)
                else:
                    w.kompleks = None
            elif k == "tanggal_lahir":
                if v:
                    try:
                        w.tanggal_lahir = datetime.strptime(v, "%Y-%m-%d").date()
                    except ValueError:
                        pass
                else:
                    w.tanggal_lahir = None
            elif hasattr(w, k):
                setattr(w, k, v)
        w.save()
        return {
            "id": w.id,
            "nama_lengkap": w.nama_lengkap,
            "nik": w.nik,
            "alamat": f"Blok {w.kompleks.blok}/{w.kompleks.nomor}"
            if w.kompleks
            else "Tidak ada alamat",
        }


class AgentService:
    def __init__(self, ai_provider: BaseAIProvider):
        self.ai_provider = ai_provider

    def run_agent_turn(
        self,
        messages: list[dict],
        system_adapter: SystemAdapter,
        correlation_id: str = None,
    ) -> str:
        messages_with_system = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
        from kependudukan.ai.ai_utils import parse_extracted_json

        # Allow the agent to perform up to 5 steps of sequential tool calls
        for iteration in range(5):
            try:
                raw_response = self.ai_provider.chat_completion(
                    messages=messages_with_system,
                    response_format={"type": "json_object"},
                    correlation_id=correlation_id,
                )
                logger.info(
                    f"Agent raw response (iteration {iteration + 1}): {raw_response}"
                )

                parsed = parse_extracted_json(raw_response)
                parsed.get("thought", "")
                tool_call = parsed.get("tool_call")
                reply = parsed.get("reply", "")

                if tool_call and isinstance(tool_call, dict) and tool_call.get("name"):
                    tool_name = tool_call.get("name")
                    args = tool_call.get("arguments", {})

                    logger.info(
                        f"Agent calling tool: {tool_name} with args {args} (iteration {iteration + 1})"
                    )
                    tool_result = self.execute_tool(tool_name, args, system_adapter)
                    logger.info(f"Tool result: {tool_result}")

                    # Append the assistant's turn and the system tool result back to the conversation
                    messages_with_system.append(
                        {"role": "assistant", "content": raw_response}
                    )
                    messages_with_system.append(
                        {
                            "role": "user",
                            "content": f"[SYSTEM: Tool result for {tool_name}: {json.dumps(tool_result)}]",
                        }
                    )
                    # Continue loop to allow agent to react or call subsequent tools
                    continue

                # No tool calls, we have the final conversational reply
                return reply

            except Exception as e:
                logger.error(
                    f"Error in AgentService turn at iteration {iteration + 1}: {str(e)}",
                    exc_info=True,
                )
                return "Maaf, terjadi kesalahan pada sistem kecerdasan buatan kami."

        # If we hit the iteration limit, return a fallback message
        return "Permintaan Anda sedang diproses, silakan periksa status data Anda kembali nanti."

    def execute_tool(self, tool_name: str, args: dict, system_adapter: SystemAdapter):
        try:
            if tool_name == "search_warga":
                return system_adapter.search_warga(args.get("query", ""))
            elif tool_name == "get_warga_detail":
                return system_adapter.get_warga_detail(int(args.get("warga_id", 0)))
            elif tool_name == "search_kompleks":
                return system_adapter.search_kompleks(args.get("query", ""))
            elif tool_name == "get_kompleks_detail":
                return system_adapter.get_kompleks_detail(
                    int(args.get("kompleks_id", 0))
                )
            elif tool_name == "check_iuran":
                try:
                    tahun = int(args.get("tahun", 0))
                except (ValueError, TypeError):
                    tahun = datetime.now().year
                return system_adapter.check_iuran(args.get("blok_no", ""), tahun)
            elif tool_name == "add_warga":
                return system_adapter.add_warga(args)
            elif tool_name == "update_warga":
                return system_adapter.update_warga(
                    int(args.get("warga_id", 0)), args.get("updates", {})
                )
            else:
                return {"error": f"Tool '{tool_name}' not found."}
        except Exception as e:
            logger.error(f"Tool execution failed: {str(e)}", exc_info=True)
            return {"error": str(e)}


class AgentConversation:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.messages: list[dict] = []
        self.last_updated = datetime.now()

    def add_user_message(self, content: str):
        self.messages.append({"role": "user", "content": content})
        self.last_updated = datetime.now()
        self.prune()

    def add_assistant_message(self, content: str):
        self.messages.append({"role": "assistant", "content": content})
        self.last_updated = datetime.now()
        self.prune()

    def add_system_message(self, content: str):
        self.messages.append({"role": "user", "content": f"[SYSTEM: {content}]"})
        self.last_updated = datetime.now()
        self.prune()

    def clear(self):
        self.messages = []
        self.last_updated = datetime.now()

    def prune(self, max_messages=20):
        if len(self.messages) > max_messages:
            self.messages = self.messages[-max_messages:]
