"""Ollama LLM interface for hypothesis generation."""

import logging
from pathlib import Path
from typing import List, Optional, Any

from physai.core.types import Variable, Attempt
from physai.utils.feedback import (
    extract_wolfram_expression,
    format_error_history,
    generate_error_feedback,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "system_prompt.txt"


class OllamaInterfaceError(Exception):
    """Base exception for OllamaInterface errors."""


class OllamaConnectionError(OllamaInterfaceError):
    """Raised when connection to Ollama server fails."""


class OllamaGenerationError(OllamaInterfaceError):
    """Raised when generation fails."""


class OllamaInterface:
    """
    Interface to Ollama for generating Wolfram Language hypotheses.

    This class wraps the Ollama API and provides:
    - Structured prompts for physics equation generation
    - Few-shot examples for consistent output format
    - Error history integration for iterative refinement

    Usage:
        >>> interface = OllamaInterface(model="granite4:1b")
        >>> hypothesis = interface.generate_hypothesis(
        ...     target=Variable("period", "Seconds"),
        ...     inputs=[Variable("length", "Meters")],
        ...     error_history=[]
        ... )
    """

    def __init__(
        self,
        model: str = "granite4:1b",
        base_url: str = "http://localhost:11434",
        timeout: int = 60,
        temperature: float = 0.7,
        system_prompt_path: Optional[Path] = None,
    ):
        """
        Initialize the Ollama interface.

        Args:
            model: Name of the Ollama model to use.
            base_url: URL of the Ollama server.
            timeout: Request timeout in seconds.
            temperature: Sampling temperature (0.0 to 1.0).
            system_prompt_path: Path to custom system prompt file.
        """
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.temperature = temperature
        self._client = None

        prompt_path = system_prompt_path or SYSTEM_PROMPT_PATH
        self._system_prompt = self._load_system_prompt(prompt_path)

    def _load_system_prompt(self, path: Path) -> str:
        """Load the system prompt from file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"System prompt file not found at {path}, using default")
            return self._get_default_system_prompt()

    def _get_default_system_prompt(self) -> str:
        """Return a minimal default system prompt."""
        # The long line below is prompt text sent verbatim to the model.
        # Wrapping it would insert a newline into the prompt.
        # pylint: disable=line-too-long
        return """You are a Physics Equation Synthesizer. Output ONLY valid Wolfram Language expressions.
No markdown. No explanation. Just the expression.

Example:
Target: period [Time]
Inputs: length [Length]
Output: a * Sqrt[length]
"""

    def _ensure_client(self) -> Any:
        """Ensure Ollama client is available."""
        if self._client is not None:
            return self._client

        try:
            # optional backend: ollama is imported lazily so the module loads without it
            import ollama  # pylint: disable=import-outside-toplevel

            self._client = ollama.Client(host=self.base_url)
            return self._client
        except ImportError as e:
            raise OllamaConnectionError(
                "ollama package is required. Install with: pip install ollama"
            ) from e

    def check_connection(self) -> bool:
        """
        Check if Ollama server is reachable.

        Returns:
            True if connection is successful, False otherwise.
        """
        try:
            client = self._ensure_client()
            client.list()
            return True
        # foreign boundary: the ollama client raises httpx types this package does not depend on
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to connect to Ollama: {e}")
            return False

    def list_models(self) -> List[str]:
        """
        List available models on the Ollama server.

        Returns:
            List of model names.
        """
        client = self._ensure_client()
        try:
            response = client.list()
            return [
                m.get("model", m.get("name", "")) for m in response.get("models", [])
            ]
        # foreign boundary: the ollama client raises httpx types this package does not depend on
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to list models: {e}")
            return []

    def generate_hypothesis(
        self,
        target: Variable,
        inputs: List[Variable],
        error_history: Optional[List[Attempt]] = None,
        feedback: Optional[str] = None,
        max_history: int = 5,
    ) -> str:
        """
        Generate a Wolfram Language hypothesis for the target variable.

        Args:
            target: Target variable to predict.
            inputs: List of input variables.
            error_history: Previous failed attempts for learning.
            feedback: Qualitative feedback from last attempt.
            max_history: Maximum number of history entries to include.

        Returns:
            Wolfram Language expression string.

        Raises:
            OllamaGenerationError: If generation fails.
        """
        client = self._ensure_client()

        if error_history is None:
            error_history = []

        prompt = self._build_prompt(
            target=target,
            inputs=inputs,
            error_history=error_history[-max_history:] if error_history else [],
            feedback=feedback or "",
        )

        try:
            response = client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": prompt},
                ],
                options={
                    "temperature": self.temperature,
                    "num_predict": 256,
                },
            )

            raw_output = response.get("message", {}).get("content", "")

            if not raw_output:
                raise OllamaGenerationError("Empty response from model")

            expression = extract_wolfram_expression(raw_output)

            if not expression:
                raise OllamaGenerationError(
                    f"Could not extract expression from output: {raw_output[:100]}"
                )

            logger.debug(f"Generated expression: {expression}")
            return expression

        except OllamaGenerationError:
            raise
        except Exception as e:
            raise OllamaGenerationError(f"Generation failed: {e}") from e

    def _build_prompt(
        self,
        target: Variable,
        inputs: List[Variable],
        error_history: List[Attempt],
        feedback: str,
    ) -> str:
        """
        Build the user prompt with variable metadata and history.

        Args:
            target: Target variable.
            inputs: Input variables.
            error_history: Previous attempts.
            feedback: Feedback string.

        Returns:
            Formatted prompt string.
        """
        inputs_formatted = ", ".join(f"{v.name} [{v.unit}]" for v in inputs)

        history_str = (
            format_error_history(error_history)
            if error_history
            else "No previous attempts."
        )

        prompt = f"""Target: {target.name} [{target.unit}]
Inputs: {inputs_formatted}

Previous attempts:
{history_str}

{f"Feedback: {feedback}" if feedback else "This is the first attempt."}

Output:"""

        return prompt

    def generate_with_retry(
        self,
        target: Variable,
        inputs: List[Variable],
        error_history: Optional[List[Attempt]] = None,
        max_retries: int = 3,
    ) -> str:
        """
        Generate a hypothesis with automatic retry on failure.

        Args:
            target: Target variable.
            inputs: Input variables.
            error_history: Previous failed attempts.
            max_retries: Maximum number of retries.

        Returns:
            Wolfram Language expression string.
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                feedback = None
                if error_history and attempt > 0:
                    last_attempt = error_history[-1]
                    feedback = generate_error_feedback(last_attempt)

                return self.generate_hypothesis(
                    target=target,
                    inputs=inputs,
                    error_history=error_history,
                    feedback=feedback,
                )
            except OllamaGenerationError as e:
                last_error = e
                logger.warning(f"Generation attempt {attempt + 1} failed: {e}")

        raise OllamaGenerationError(
            f"Failed after {max_retries} attempts. Last error: {last_error}"
        )
