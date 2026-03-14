"""
ARGUS Agents — SecureToolExecutor: safe command execution with allowlist and hard deny.
No shell=True; args as list; AWS profile/region injection.
Guardrails per AGENT_ACCESS_MODEL.md §5.
"""
import asyncio
import re
import shlex
import unicodedata
from dataclasses import dataclass
from typing import Optional

from agents.config import AWS_PROFILE, AWS_REGION, logger


@dataclass
class CommandResult:
    """Result of executing a command."""
    stdout: str
    stderr: str
    returncode: int


# Allowlist: only these patterns may execute (AGENT_ACCESS_MODEL §5.1 + phase-3 needs)
ALLOWED_COMMAND_PATTERNS = [
    r"^aws ec2 describe-",
    r"^aws ec2 get-",
    r"^aws ec2 list-",
    r"^aws iam list-",
    r"^aws iam get-",
    r"^aws iam generate-credential-report$",
    r"^aws rds describe-",
    r"^aws s3api get-bucket-",
    r"^aws s3api list-",
    r"^aws cloudwatch describe-",
    r"^aws cloudwatch get-",
    r"^aws cloudtrail describe-",
    r"^aws cloudtrail get-trail-status",
    r"^aws sns list-",
    r"^aws sns get-",
    r"^aws kms list-",
    r"^aws kms describe-",
    r"^aws kms get-key-rotation-status",
    r"^aws logs describe-",
    r"^aws sts get-caller-identity$",
    r"^aws config describe-",
    r"^aws secretsmanager list-",
    r"^aws lambda list-",
]

# Hard deny: reject before allowlist check (AGENT_ACCESS_MODEL §5.2)
# Note: We run with create_subprocess_exec (no shell), so literal $ is safe. We still block
# shell substitution: $(...) and ${...}. Semicolon, pipe, backtick stay denied.
HARD_DENY_PATTERNS = [
    r"[;&|`]",   # shell chaining/pipe/backtick; allow $ so --query "..." and JMESPath work
    r"\$\(",     # $(...) command substitution
    r"\$\{",     # ${...} variable expansion
    r">\s*[/\w]",
    r"<\(",
    r"\|\s*bash",
    r"\|\s*sh",
    r"\bchmod\b",
    r"\bchown\b",
    r"\btouch\b",
    r"\bmkdir\b",
    r"\brm\b",
    r"\bmv\b",
    r"\bcp\b",
    r"\bwget\b",
    r"\bcurl\b.*-o\s",
    r"\btee\b",
    r"\bdd\b",
    r"\bapt\b",
    r"\byum\b",
    r"\bpip\b",
    r"\bnpm\b",
    r"\binstall\b",
    r"\bsudo\b",
    r"\bsu\s",
    r"\bpasswd\b",
    r"\busermod\b",
    r"\bvisudo\b",
    r"\bnc\b.*-e",
    r"\bbash\b.*-i",
    r"\bpython.*socket",
    r"/dev/tcp",
    r"aws\s+\w+\s+(create|delete|modify|put|update|run|start|stop|terminate|attach|detach|authorize|revoke)",
    r"169\.254\.169\.254",
    r"fd00:ec2::254",
    r"curl.*attacker",
    r"wget.*attacker",
    r"\bdnscat\b",
    r"base64.*\|.*curl",
    r"ProxyCommand",
    r"LocalCommand",
    r"StrictHostKeyChecking=no",
    r"UserKnownHostsFile=/dev/null",
]

_ALLOWED_RE = [re.compile(p) for p in ALLOWED_COMMAND_PATTERNS]
_DENY_RE = [re.compile(p, re.IGNORECASE) for p in HARD_DENY_PATTERNS]


def _normalize_unicode(s: str) -> str:
    """Normalize homoglyphs (e.g. fullwidth 'ａｗｓ' -> 'aws')."""
    return unicodedata.normalize("NFKC", s)


def _matches_allowlist(command: str) -> bool:
    """True if command matches at least one allowed pattern."""
    for pat in _ALLOWED_RE:
        if pat.search(command):
            return True
    return False


def _matches_deny(command: str) -> Optional[str]:
    """If command matches any deny pattern, return that pattern; else None."""
    for pat in _DENY_RE:
        if pat.search(command):
            return pat.pattern
    return None


class SecureToolExecutor:
    """Execute AWS CLI commands safely. No shell interpretation."""

    def __init__(
        self,
        profile: Optional[str] = None,
        region: Optional[str] = None,
    ):
        self.profile = profile or AWS_PROFILE
        self.region = region or AWS_REGION

    def _inject_aws_args(self, command: str) -> str:
        """Ensure --profile and --region are present in AWS CLI commands."""
        cmd_stripped = command.strip()
        if cmd_stripped.startswith("aws ") and "--profile" not in command:
            command = command.rstrip() + f" --profile {self.profile} --region {self.region}"
        return command

    async def execute(
        self,
        command: str,
        timeout: int = 30,
    ) -> CommandResult:
        """
        Execute command after normalization, deny check, and allowlist check.
        Uses subprocess exec (no shell). Returns CommandResult; on denial, returncode != 0 and stderr explains.
        """
        command = _normalize_unicode(command).strip()
        cmd_preview = (command[:80] + "…") if len(command) > 80 else command

        if not command:
            logger.warning("executor: command denied (empty)")
            return CommandResult(
                stdout="",
                stderr="Command denied: empty command.",
                returncode=-1,
            )

        deny_reason = _matches_deny(command)
        if deny_reason is not None:
            logger.warning("executor: command denied (deny pattern) command=%s pattern=%s", cmd_preview, deny_reason)
            return CommandResult(
                stdout="",
                stderr=f"Command denied: matched deny pattern. Suggest an alternative.",
                returncode=-1,
            )

        if not _matches_allowlist(command):
            logger.warning("executor: command denied (not in allowlist) command=%s", cmd_preview)
            return CommandResult(
                stdout="",
                stderr="Command denied: not in allowlist. Suggest an alternative.",
                returncode=-1,
            )

        command = self._inject_aws_args(command)
        logger.info("executor: executing command=%s timeout=%s", cmd_preview, timeout)

        try:
            args = shlex.split(command)
            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout_data, stderr_data = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
                out = CommandResult(
                    stdout=stdout_data.decode("utf-8", errors="ignore"),
                    stderr=stderr_data.decode("utf-8", errors="ignore"),
                    returncode=process.returncode,
                )
                logger.info(
                    "executor: result allowed returncode=%s stdout_len=%s stderr_len=%s",
                    out.returncode, len(out.stdout), len(out.stderr),
                )
                return out
            except asyncio.TimeoutError:
                process.kill()
                logger.warning("executor: timeout command=%s timeout=%s", cmd_preview, timeout)
                return CommandResult(
                    stdout="",
                    stderr=f"Command timeout after {timeout}s",
                    returncode=-1,
                )
        except Exception as e:
            logger.exception("executor: execution error command=%s", cmd_preview)
            return CommandResult(
                stdout="",
                stderr=f"Execution error: {str(e)}",
                returncode=-1,
            )
