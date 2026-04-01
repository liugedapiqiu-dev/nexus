from __future__ import annotations

"""
Layer: runtime
Status: primary
Boundary: stable HTTP bridge contract for OpenClaw ingress; runtime-owned facade, legacy hosts may mount it.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from runtime.heart_bridge import runtime_heart


class OpenClawContext(BaseModel):
    is_dm: Optional[bool] = None
    is_group: Optional[bool] = None
    mentioned: Optional[bool] = None


class OpenClawIngressRequest(BaseModel):
    session_id: Optional[str] = None
    channel: Optional[str] = None
    channel_id: Optional[str] = None
    message_id: Optional[str] = None
    sender_id: Optional[str] = None
    sender_name: Optional[str] = None
    text: str = ""
    raw: Dict[str, Any] = Field(default_factory=dict)
    context: OpenClawContext = Field(default_factory=OpenClawContext)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OpenClawPostprocessRequest(BaseModel):
    trace_id: Optional[str] = None
    session_id: Optional[str] = None
    channel: Optional[str] = None
    channel_id: Optional[str] = None
    message_id: Optional[str] = None
    user_text: Optional[str] = None
    assistant_text: Optional[str] = None
    mode: Optional[str] = None
    latency_ms: Optional[int] = None
    success: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OpenClawBridge:
    contract_version = 'vb-openclaw-bridge-v1'

    def _trace_id(self) -> str:
        return f"vb_{uuid.uuid4().hex[:12]}"

    def _base_response(self, trace_id: str) -> Dict[str, Any]:
        return {
            'ok': True,
            'contract_version': self.contract_version,
            'mode': 'pass_through',
            'prepend_prompt': '',
            'append_prompt': '',
            'memory_context': [],
            'response_guidance': {},
            'direct_response': None,
            'trace_id': trace_id,
            'degraded': False,
            'reason': '',
            'compat': {
                'legacy_memory_save_available': True,
                'legacy_api_host': 'connector.api_server',
            },
        }

    def _decide_mode(self, text: str) -> str:
        lowered = (text or '').strip().lower()
        if not lowered:
            return 'fail_open'

        direct_prefixes = (
            '只回 ', '只回复 ', '直接回复 ', '帮我回复 ', '代我回复 ',
            'reply only:', 'reply-only:', 'just reply:'
        )
        if any(lowered.startswith(p) for p in direct_prefixes):
            return 'direct_handle'

        memory_hints = (
            '记得', '记住', 'remember this', '不要忘',
            '上次', '之前', '还记得', '我们之前'
        )
        if any(h in lowered for h in memory_hints):
            return 'enrich_prompt'

        return 'pass_through'

    def preprocess(self, req: OpenClawIngressRequest) -> Dict[str, Any]:
        trace_id = self._trace_id()
        response = self._base_response(trace_id)
        text = (req.text or '').strip()

        if not text:
            response.update({
                'ok': False,
                'mode': 'fail_open',
                'degraded': True,
                'reason': 'empty_text',
            })
            return response

        try:
            packet = runtime_heart.build_preprocess_packet(
                text,
                session_id=req.session_id,
                write_memory=False,
                tags=['openclaw_bridge', req.channel or 'unknown'],
            )
            response['prepend_prompt'] = packet.get('assistant_prompt_prefix') or ''
            response['append_prompt'] = packet.get('assistant_prompt_append') or ''
            response['response_guidance'] = {
                'heart': packet.get('reply_guidance') or {},
                'risk_flags': packet.get('risk_flags') or {},
            }
            memory_brief = packet.get('memory_brief')
            if memory_brief:
                response['memory_context'] = [memory_brief]
        except Exception as e:
            response.update({
                'mode': 'fail_open',
                'degraded': True,
                'reason': f'heart_preprocess_failed:{e.__class__.__name__}',
            })
            return response

        mode = self._decide_mode(text)
        response['mode'] = mode
        if mode == 'enrich_prompt':
            response['reason'] = 'memory_or_context_enrichment'
        elif mode == 'direct_handle':
            guidance = response.get('response_guidance', {}).get('heart', {})
            opening = guidance.get('opening') or 'direct'
            tone = guidance.get('tone') or 'natural'
            reply = text
            for prefix in ['只回 ', '只回复 ', '直接回复 ', '帮我回复 ', '代我回复 ']:
                if reply.startswith(prefix):
                    reply = reply[len(prefix):].strip()
                    break
            for prefix in ['reply only:', 'reply-only:', 'just reply:']:
                if reply.lower().startswith(prefix):
                    reply = reply[len(prefix):].strip()
                    break
            response['direct_response'] = {
                'text': reply,
                'meta': {
                    'opening': opening,
                    'tone': tone,
                    'generated_by': 'vb_openclaw_bridge_minimal_direct_handle',
                },
            }
            response['reason'] = 'minimal_direct_handle_rule'
        else:
            response['reason'] = 'default_pass_through'
        return response

    def postprocess(self, req: OpenClawPostprocessRequest) -> Dict[str, Any]:
        return {
            'ok': True,
            'contract_version': self.contract_version,
            'trace_id': req.trace_id or self._trace_id(),
            'accepted': True,
            'stored': False,
            'reason': 'postprocess_ack_minimal',
            'timestamp': datetime.now().isoformat(),
        }

    def ready(self) -> Dict[str, Any]:
        return {
            'status': 'ready',
            'contract_version': self.contract_version,
            'timestamp': datetime.now().isoformat(),
        }

    def health(self) -> Dict[str, Any]:
        return {
            'status': 'healthy',
            'bridge': 'ok',
            'contract_version': self.contract_version,
            'legacy_connector_role': 'compatibility_host_only',
            'timestamp': datetime.now().isoformat(),
        }


openclaw_bridge = OpenClawBridge()
