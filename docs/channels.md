# Channel Integrations

VaultBot supports 25+ messaging platforms through its `PlatformAdapter` protocol.

## Supported Platforms

| Platform | Module | Status |
|----------|--------|--------|
| Telegram | `platforms/telegram.py` | Stable |
| Discord | `platforms/discord.py` | Stable |
| Slack | `platforms/slack.py` | Stable |
| WhatsApp | `platforms/whatsapp.py` | Stable |
| Signal | `platforms/signal.py` | Stable |
| Teams | `platforms/teams.py` | Stable |
| Matrix | `platforms/matrix.py` | Stable |
| IRC | `platforms/irc.py` | Stable |
| Mattermost | `platforms/mattermost.py` | Stable |
| LINE | `platforms/line.py` | Stable |
| Google Chat | `platforms/googlechat.py` | Stable |
| Twitch | `platforms/twitch.py` | Stable |
| Nostr | `platforms/nostr.py` | Stable |
| iMessage | `platforms/imessage.py` | Stable |
| QQ | `platforms/qq.py` | Stable |
| Feishu/Lark | `platforms/feishu.py` | Stable |
| WeChat | `platforms/wechat.py` | Stable |
| Zalo | `platforms/zalo.py` | Stable |
| Rocket.Chat | `platforms/rocketchat.py` | Stable |
| Zulip | `platforms/zulip.py` | Stable |
| Webhook Bridge | `platforms/webhook_bridge.py` | Stable |

## Adding a New Platform

Implement the `PlatformAdapter` protocol from `platforms/base.py`:

```python
class MyPlatformAdapter:
    @property
    def platform_name(self) -> str: ...
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def listen(self) -> AsyncIterator[InboundMessage]: ...
    async def send(self, message: OutboundMessage) -> None: ...
    async def healthcheck(self) -> bool: ...
```
