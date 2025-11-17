import asyncio
import re
import ssl
import certifi
from typing import Optional
from aiohttp import ClientSession, ClientTimeout, TCPConnector
from httpx import AsyncClient
from src.logger import logger


class Solvium:

    def __init__(self, api_key: str, session: AsyncClient, proxy: Optional[str] = None):
        self.api_key = api_key
        self.proxy = proxy
        self.base_url = "https://captcha.solvium.io/api/v1"
        self.session = session

    def _format_proxy(self, proxy: str) -> str:

        if not proxy:
            return None
        if "@" in proxy:
            return proxy
        return f"http://{proxy}"

    async def create_turnstile_task(self, sitekey: str, pageurl: str) -> Optional[str]:

        headers = {"Authorization": f"Bearer {self.api_key}"}
        url = f"{self.base_url}/task/turnstile?url={pageurl}&sitekey={sitekey}"

        try:
            response = await self.session.get(url, headers=headers, timeout=30)
            result = response.json()

            if result.get("message") == "Task created" and "task_id" in result:
                return result["task_id"]

            logger.error(f"Error creating Turnstile task with Solvium: {result}")
            return None

        except Exception as e:
            logger.error(f"Error creating Turnstile task with Solvium: {e}")
            return None

    async def get_task_result(self, task_id: str) -> Optional[str]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        max_attempts = 30

        for _ in range(max_attempts):
            try:
                response = await self.session.get(
                    f"{self.base_url}/task/status/{task_id}",
                    headers=headers,
                    timeout=30,
                )
                result = response.json()

                if result.get("status") == "completed" and result.get("result") and result["result"].get("solution"):
                    solution = result["result"]["solution"]
                    if re.match(r'^[a-zA-Z0-9\.\-_]+$', solution):
                        return solution
                    else:
                        logger.error(f"Invalid solution format from Solvium: {solution}")
                        return None

                elif result.get("status") in ["running", "pending"]:
                    await asyncio.sleep(5)
                    continue
                else:
                    logger.error(f"Error getting result with Solvium: {result}")
                    return None

            except Exception as e:
                logger.error(f"Error getting result with Solvium: {e}")
                return None

        logger.error("Max polling attempts reached without getting a result with Solvium")
        return None

    async def solve_captcha(self, sitekey: str, pageurl: str) -> Optional[str]:
        task_id = await self.create_turnstile_task(sitekey, pageurl)
        if not task_id:
            return None
        return await self.get_task_result(task_id)


class TwoCaptcha:

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "http://2captcha.com"

        try:
            self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            self.ssl_context = ssl.create_default_context()

    async def solve_turnstile(self, sitekey: str, pageurl: str, retries: int = 5) -> Optional[str]:
        for attempt in range(retries):
            try:
                connector = TCPConnector(ssl=self.ssl_context)
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    # Create task
                    url = f"{self.base_url}/in.php?key={self.api_key}&method=turnstile&sitekey={sitekey}&pageurl={pageurl}"
                    async with session.get(url=url) as response:
                        response.raise_for_status()
                        result = await response.text()

                        if 'OK|' not in result:
                            logger.warning(f"2Captcha response: {result}")
                            await asyncio.sleep(5)
                            continue

                        request_id = result.split('|')[1]
                        logger.debug(f"2Captcha Request ID: {request_id}")

                        # Wait for solution
                        for _ in range(30):
                            res_url = f"{self.base_url}/res.php?key={self.api_key}&action=get&id={request_id}"
                            async with session.get(url=res_url) as res_response:
                                res_response.raise_for_status()
                                res_result = await res_response.text()

                                if 'OK|' in res_result:
                                    turnstile_token = res_result.split('|')[1]
                                    logger.success("Turnstile solved successfully via 2Captcha")
                                    return turnstile_token

                                elif res_result == "CAPCHA_NOT_READY":
                                    logger.debug("Captcha not ready, waiting...")
                                    await asyncio.sleep(5)
                                    continue
                                else:
                                    break

            except Exception as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                logger.error(f"2Captcha error: {str(e)}")
                return None

        return None


class CaptchaSolver:

    def __init__(self, provider: str, api_key: str):
        self.provider = provider.lower()
        self.api_key = api_key

        if not api_key:
            logger.warning(f"No API key provided for {provider}")

    async def solve_turnstile(self, sitekey: str, pageurl: str) -> Optional[str]:
        if not self.api_key:
            logger.error("Captcha API key is not set")
            return None

        logger.info(f"Solving captcha using {self.provider.upper()}...")

        if self.provider == "solvium":
            async with AsyncClient(timeout=60) as client:
                solver = Solvium(api_key=self.api_key, session=client)
                return await solver.solve_captcha(sitekey, pageurl)

        elif self.provider == "2captcha":
            solver = TwoCaptcha(api_key=self.api_key)
            return await solver.solve_turnstile(sitekey, pageurl)

        else:
            logger.error(f"Unknown captcha provider: {self.provider}")
            return None