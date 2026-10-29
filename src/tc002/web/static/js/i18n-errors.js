// Titles of the server's errors (RFC 9457 problem types), keyed by the type's last path
// segment, so a failure reads in the UI's language. The detail stays as the server sent it.

export const en = {
  "err.clock-refused-the-request": "Clock refused the request", "err.clock-unreachable": "Clock unreachable",
  "err.cross-site-request": "Cross-site request", "err.empty-message": "Empty message",
  "err.invalid-address": "Invalid address", "err.invalid-settings": "Invalid settings",
  "err.malformed-json": "Malformed request", "err.missing-token": "Missing token",
  "err.no-clock-configured": "No clock configured", "err.no-clock-there": "No clock at that address",
  "err.no-tc002.toml": "No tc002.toml", "err.not-found": "Not found", "err.not-on-the-clock": "Not on the clock",
  "err.nothing-to-change": "Nothing to change", "err.nothing-to-show": "Nothing to show",
  "err.request-failed": "Request failed", "err.too-large": "Request too large",
  "err.unknown-preset": "Unknown preset", "err.unknown-preview": "Unknown preview",
  "err.unknown-screen": "Unknown screen", "err.wrong-host": "Wrong address",
};

export const zh = {
  "err.clock-refused-the-request": "时钟拒绝了请求", "err.clock-unreachable": "连不上时钟",
  "err.cross-site-request": "跨站请求被拒绝", "err.empty-message": "消息为空",
  "err.invalid-address": "地址无效", "err.invalid-settings": "设置无效",
  "err.malformed-json": "请求格式错误", "err.missing-token": "缺少令牌",
  "err.no-clock-configured": "还没有设置时钟", "err.no-clock-there": "这个地址没有时钟",
  "err.no-tc002.toml": "没有 tc002.toml", "err.not-found": "未找到", "err.not-on-the-clock": "时钟上没有这个应用",
  "err.nothing-to-change": "没有需要修改的内容", "err.nothing-to-show": "没有可显示的内容",
  "err.request-failed": "请求失败", "err.too-large": "请求过大",
  "err.unknown-preset": "未知的预设", "err.unknown-preview": "未知的预览",
  "err.unknown-screen": "未知的画面", "err.wrong-host": "地址不对",
};
