import abc
import base64
import logging
import time
import uuid
import requests
from django.conf import settings
from kependudukan.ai.ai_utils import parse_extracted_json, map_extracted_data

logger = logging.getLogger(__name__)

PROMPT = (
    "Extract the following fields from the KTP (Indonesian Identity Card) image:\n"
    "1. NIK (16-digit number, remove spaces/dots)\n"
    "2. Nama (Full name as written on KTP)\n"
    "3. Alamat (Full address, street, block, number, RT/RW, etc.)\n"
    "4. Jenis Kelamin (Gender: output either 'LAKI-LAKI' or 'PEREMPUAN')\n"
    "5. Agama (Religion: output either 'ISLAM', 'KATHOLIK', 'KRISTEN', 'HINDU', 'BUDDHA', or 'KONGHUCU')\n"
    "6. Tempat Lahir (Place of birth, e.g. 'JAKARTA')\n"
    "7. Tanggal Lahir (Date of birth in DD-MM-YYYY format, e.g. '31-12-2026')\n\n"
    "You must respond ONLY with a raw JSON object containing these keys: "
    '"nik", "nama", "alamat_ktp", "jenis_kelamin", "agama", "tempat_lahir", "tanggal_lahir". '
    "Do not include any explanation or markdown formatting."
)


class BaseAIProvider(abc.ABC):
    @abc.abstractmethod
    def extract_ktp_data(self, image_bytes: bytes, correlation_id: str = None) -> dict:
        """
        Sends the image to the AI model and returns a dictionary of raw extracted fields.
        """
        pass

    @abc.abstractmethod
    def get_remaining_quota(self, correlation_id: str = None) -> float | None:
        """
        Returns the remaining quota or balance. Returns None if unlimited or unsupported.
        """
        pass

    @abc.abstractmethod
    def chat_completion(
        self,
        messages: list[dict],
        response_format: dict = None,
        correlation_id: str = None,
    ) -> str:
        """
        Sends conversation history to the AI model and returns the response string.
        """
        pass

    def is_quota_low(self, correlation_id: str = None) -> bool:
        """
        Checks if the quota is low based on the configured warning threshold.
        """
        remaining = self.get_remaining_quota(correlation_id)
        if remaining is None:
            return False
        return remaining < getattr(settings, "OPENROUTER_QUOTA_THRESHOLD", 1.0)


class OllamaProvider(BaseAIProvider):
    def extract_ktp_data(self, image_bytes: bytes, correlation_id: str = None) -> dict:
        corr_id = correlation_id or str(uuid.uuid4())
        url = f"{settings.OLLAMA_API_URL}/api/chat"
        model = settings.OLLAMA_MODEL

        logger.info(
            f"[AI_EXTRACT_START] [CorrelationID: {corr_id}] "
            f"Provider: Ollama, Model: {model}, URL: {url}, Size: {len(image_bytes)} bytes"
        )

        base64_image = base64.b64encode(image_bytes).decode("utf-8")

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": PROMPT, "images": [base64_image]}],
            "stream": False,
            "options": {"temperature": 0.0},
        }

        headers = {}
        api_key = getattr(settings, "OLLAMA_API_KEY", None)
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        start_time = time.time()
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            duration_ms = int((time.time() - start_time) * 1000)

            if response.status_code != 200:
                logger.error(
                    f"[AI_EXTRACT_FAIL] [CorrelationID: {corr_id}] "
                    f"HTTP Status: {response.status_code}, Error: {response.text}"
                )
                raise RuntimeError(
                    f"Ollama server returned status code {response.status_code}"
                )

            resp_data = response.json()
            message_content = resp_data.get("message", {}).get("content", "")

            logger.info(
                f"[AI_EXTRACT_SUCCESS] [CorrelationID: {corr_id}] "
                f"Duration: {duration_ms}ms, Content length: {len(message_content)}"
            )

            raw_dict = parse_extracted_json(message_content)
            return map_extracted_data(raw_dict)

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                f"[AI_EXTRACT_FAIL] [CorrelationID: {corr_id}] "
                f"Duration: {duration_ms}ms, Exception: {str(e)}",
                exc_info=True,
            )
            raise

    def get_remaining_quota(self, correlation_id: str = None) -> float | None:
        # Ollama runs locally and has unlimited quota
        return None

    def chat_completion(
        self,
        messages: list[dict],
        response_format: dict = None,
        correlation_id: str = None,
    ) -> str:
        corr_id = correlation_id or str(uuid.uuid4())
        url = f"{settings.OLLAMA_API_URL}/api/chat"
        model = settings.OLLAMA_MODEL

        logger.info(
            f"[AI_CHAT_START] [CorrelationID: {corr_id}] "
            f"Provider: Ollama, Model: {model}, URL: {url}, Messages: {len(messages)}"
        )

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.0},
        }

        if response_format and response_format.get("type") == "json_object":
            payload["format"] = "json"

        headers = {}
        api_key = getattr(settings, "OLLAMA_API_KEY", None)
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        start_time = time.time()
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            duration_ms = int((time.time() - start_time) * 1000)

            if response.status_code != 200:
                logger.error(
                    f"[AI_CHAT_FAIL] [CorrelationID: {corr_id}] "
                    f"HTTP Status: {response.status_code}, Error: {response.text}"
                )
                raise RuntimeError(
                    f"Ollama server returned status code {response.status_code}"
                )

            resp_data = response.json()
            message_content = resp_data.get("message", {}).get("content", "")

            logger.info(
                f"[AI_CHAT_SUCCESS] [CorrelationID: {corr_id}] "
                f"Duration: {duration_ms}ms, Content length: {len(message_content)}"
            )

            return message_content

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                f"[AI_CHAT_FAIL] [CorrelationID: {corr_id}] "
                f"Duration: {duration_ms}ms, Exception: {str(e)}",
                exc_info=True,
            )
            raise


class OpenRouterProvider(BaseAIProvider):
    def extract_ktp_data(self, image_bytes: bytes, correlation_id: str = None) -> dict:
        corr_id = correlation_id or str(uuid.uuid4())
        url = "https://openrouter.ai/api/v1/chat/completions"
        model = settings.OPENROUTER_MODEL
        api_key = settings.OPENROUTER_API_KEY

        logger.info(
            f"[AI_EXTRACT_START] [CorrelationID: {corr_id}] "
            f"Provider: OpenRouter, Model: {model}, URL: {url}, Size: {len(image_bytes)} bytes"
        )

        if not api_key:
            logger.error(
                f"[AI_EXTRACT_FAIL] [CorrelationID: {corr_id}] "
                f"Error: OPENROUTER_API_KEY is not set."
            )
            raise ValueError("OPENROUTER_API_KEY is not configured.")

        base64_image = base64.b64encode(image_bytes).decode("utf-8")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "DataWarga",
        }

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            "response_format": {"type": "json_object"},
        }

        start_time = time.time()
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            duration_ms = int((time.time() - start_time) * 1000)

            if response.status_code != 200:
                logger.error(
                    f"[AI_EXTRACT_FAIL] [CorrelationID: {corr_id}] "
                    f"HTTP Status: {response.status_code}, Error: {response.text}"
                )
                raise RuntimeError(
                    f"OpenRouter server returned status code {response.status_code}"
                )

            resp_data = response.json()
            message_content = (
                resp_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            )

            logger.info(
                f"[AI_EXTRACT_SUCCESS] [CorrelationID: {corr_id}] "
                f"Duration: {duration_ms}ms, Content length: {len(message_content)}"
            )

            raw_dict = parse_extracted_json(message_content)
            return map_extracted_data(raw_dict)

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                f"[AI_EXTRACT_FAIL] [CorrelationID: {corr_id}] "
                f"Duration: {duration_ms}ms, Exception: {str(e)}",
                exc_info=True,
            )
            raise

    def get_remaining_quota(self, correlation_id: str = None) -> float | None:
        corr_id = correlation_id or str(uuid.uuid4())
        url = "https://openrouter.ai/api/v1/auth/key"
        api_key = settings.OPENROUTER_API_KEY

        logger.info(
            f"[AI_QUOTA_CHECK_START] [CorrelationID: {corr_id}] Provider: OpenRouter"
        )

        if not api_key:
            logger.warning(
                f"[AI_QUOTA_CHECK_WARN] [CorrelationID: {corr_id}] OpenRouter API key not configured."
            )
            return None

        headers = {
            "Authorization": f"Bearer {api_key}",
        }

        start_time = time.time()
        try:
            response = requests.get(url, headers=headers, timeout=10)
            duration_ms = int((time.time() - start_time) * 1000)

            if response.status_code != 200:
                logger.error(
                    f"[AI_QUOTA_CHECK_FAIL] [CorrelationID: {corr_id}] "
                    f"HTTP Status: {response.status_code}, Error: {response.text}"
                )
                return None

            resp_data = response.json()
            data = resp_data.get("data", {})
            limit_remaining = data.get("limit_remaining")

            logger.info(
                f"[AI_QUOTA_CHECK_SUCCESS] [CorrelationID: {corr_id}] "
                f"Duration: {duration_ms}ms, Limit remaining: {limit_remaining}"
            )

            if limit_remaining is not None:
                return float(limit_remaining)

            # If limit_remaining is None, but limit and usage are present
            limit = data.get("limit")
            usage = data.get("usage")
            if limit is not None and usage is not None:
                return float(limit) - float(usage)

            return None

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                f"[AI_QUOTA_CHECK_FAIL] [CorrelationID: {corr_id}] "
                f"Duration: {duration_ms}ms, Exception: {str(e)}",
                exc_info=True,
            )
            return None

    def chat_completion(
        self,
        messages: list[dict],
        response_format: dict = None,
        correlation_id: str = None,
    ) -> str:
        corr_id = correlation_id or str(uuid.uuid4())
        url = "https://openrouter.ai/api/v1/chat/completions"
        model = settings.OPENROUTER_MODEL
        api_key = settings.OPENROUTER_API_KEY

        logger.info(
            f"[AI_CHAT_START] [CorrelationID: {corr_id}] "
            f"Provider: OpenRouter, Model: {model}, URL: {url}, Messages: {len(messages)}"
        )

        if not api_key:
            logger.error(
                f"[AI_CHAT_FAIL] [CorrelationID: {corr_id}] "
                f"Error: OPENROUTER_API_KEY is not set."
            )
            raise ValueError("OPENROUTER_API_KEY is not configured.")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "DataWarga",
        }

        payload = {
            "model": model,
            "messages": messages,
        }

        if response_format:
            payload["response_format"] = response_format

        start_time = time.time()
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            duration_ms = int((time.time() - start_time) * 1000)

            if response.status_code != 200:
                logger.error(
                    f"[AI_CHAT_FAIL] [CorrelationID: {corr_id}] "
                    f"HTTP Status: {response.status_code}, Error: {response.text}"
                )
                raise RuntimeError(
                    f"OpenRouter server returned status code {response.status_code}"
                )

            resp_data = response.json()
            message_content = (
                resp_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            )

            logger.info(
                f"[AI_CHAT_SUCCESS] [CorrelationID: {corr_id}] "
                f"Duration: {duration_ms}ms, Content length: {len(message_content)}"
            )

            return message_content

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                f"[AI_CHAT_FAIL] [CorrelationID: {corr_id}] "
                f"Duration: {duration_ms}ms, Exception: {str(e)}",
                exc_info=True,
            )
            raise


def get_ai_provider() -> BaseAIProvider:
    provider_name = getattr(settings, "KTP_AI_PROVIDER", "ollama").lower()
    if provider_name == "openrouter":
        return OpenRouterProvider()
    else:
        return OllamaProvider()
