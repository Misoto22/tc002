// UI strings in English and Chinese. t("key", {var}) looks up the current language and
// falls back to English, then to the key itself, so a missing string is visible, not blank.

import * as agents from "./i18n-agents.js";
import * as errors from "./i18n-errors.js";

const en = {
  "nav.clock": "Clock", "nav.send": "Send", "nav.system": "System",
  "page.overview": "Overview", "page.rotation": "Rotation", "page.builtins": "Built-in apps",
  "page.display": "Display & sound", "page.apps": "App settings", "page.messages": "Messages",
  "page.integrations": "Integrations",
  "desc.overview": "What your clock is doing and whether it matches tc002.toml.",
  "desc.rotation": "The screens the clock cycles through, in order. Drag to reorder, or start from a preset.",
  "desc.builtins": "Apps that stay on the clock. Everything switched off is hidden from the device.",
  "desc.display": "Brightness, volume, time and date on the clock. Saved to tc002.toml and applied to the clock.",
  "desc.apps": "Options of tc002's screens and of the clock's built-in apps. Accounts and API keys stay in Ulanzi Studio.",
  "desc.messages": "Send a one-off message. It plays, then clears itself.",
  "desc.integrations": "How tc002 is wired into this Mac.",

  "status.loading": "Loading…", "status.synced": "In sync", "status.dirty": "{n} unsaved",
  "status.saving": "Saving and applying…", "status.applied": "Applied to clock",
  "status.savedOffline": "Saved — clock offline", "status.error": "Save failed",
  "status.drift": "Clock differs from tc002.toml", "status.live": "Live on clock",
  "status.liveStarting": "Sending to clock…", "activity.title": "Activity",
  "activity.empty": "Nothing yet this session.", "activity.save": "Save & apply",
  "activity.live": "Live preview", "activity.liveStop": "Live preview ended",
  "activity.show": "Show on clock", "activity.message": "Message sent",
  "activity.apply": "Apply tc002.toml", "activity.changes": "{n} change(s) on the clock",
  "activity.noChanges": "The clock already matched",

  "save.unsaved": "Unsaved changes", "save.discard": "Discard", "save.save": "Save & apply",
  "save.savedApplied": "Saved and applied", "save.serviceReloaded": "service reloaded",
  "save.saved": "Saved to tc002.toml",

  "preview.title": "Preview", "preview.live": "Live on the clock",
  "preview.liveHint": "Changes play on the hardware before you save. Turning it off restores tc002.toml.",
  "preview.liveOn": "Live · rotation paused", "preview.approx": "Approximation of the clock's own app",
  "preview.sample": "sample data", "preview.rotation": "Rotation", "preview.play": "Play",
  "preview.pause": "Pause", "preview.message": "Message draft", "preview.offline": "Clock offline: live preview unavailable",

  "row.clock": "Clock", "row.service": "Background service", "row.hooks": "Claude Code hooks",
  "row.sync": "Clock matches tc002.toml", "row.lastEvent": "Last event: {kind}, {ago}",
  "row.noEvent": "No event yet", "row.everythingSynced": "Everything in sync",
  "row.differs": "Differs: {list}", "row.customApps": "Custom apps on the clock",
  "row.customAppsHint": "Pushed by tc002 and other tools", "row.none": "None",
  "badge.online": "Online", "badge.offline": "Offline", "badge.running": "Running",
  "badge.stopped": "Stopped", "badge.inSync": "In sync", "badge.installed": "Installed",
  "badge.missing": "Missing", "badge.hooks": "{n}/3 installed",
  "btn.refresh": "Refresh", "btn.applyNow": "Apply now", "btn.retry": "Retry",
  "btn.addSlot": "Add slot", "btn.send": "Send to clock", "btn.showNow": "Show on the clock now",
  "btn.remove": "Remove", "btn.clear": "Clear",
  "section.status": "Status", "section.device": "Device", "section.behaviour": "Behaviour",
  "section.brightness": "Brightness", "section.general": "General", "section.compose": "Compose",
  "section.service": "Background service", "section.hooks": "Claude Code hooks",
  "section.config": "Configuration", "section.preferences": "Preferences",
  "fact.ip": "IP", "fact.wifi": "Wi-Fi", "fact.firmware": "Firmware", "fact.mcu": "MCU",
  "fact.mac": "MAC", "fact.serial": "Serial",

  "rotation.screen": "tc002 screen", "rotation.builtin": "Built-in app",
  "rotation.empty": "No slots: the clock's own carousel decides what to show.",
  "rotation.cycle": "One cycle: {s}s", "rotation.screens": "Screens",
  "rotation.builtins": "Built-in apps", "rotation.nothing": "Nothing to add",
  "rotation.takeover": "Alerts take over",
  "rotation.takeoverHint": "A session waiting for you takes over the clock until you answer; a finished one shows DONE briefly",
  "rotation.screenToggle": "{name} screen", "rotation.screenHint": "Run this screen in the background service",
  "rotation.drag": "Drag to reorder", "rotation.seconds": "seconds",

  "builtins.onNow": "On the clock now", "builtins.offNow": "Off on the clock",
  "builtins.linked": "account linked in Ulanzi Studio", "builtins.inRotation": "in the rotation",
  "builtins.cat.tools": "Tools", "builtins.cat.social": "Social", "builtins.cat.calendar": "Calendar",

  "display.fromClock": "Clock's own value", "display.inToml": "Set in tc002.toml",
  "display.pending": "Set in tc002.toml · not yet on the clock",
  "display.level": "Active level", "display.levelPercent": "{level} level",
  "display.percentHint": "Percent; low < mid < high", "display.carousel": "Device carousel",
  "display.carouselOff": "Off — the tc002 rotation drives the screen",
  "display.carouselDevice": "Set by the clock (no rotation)", "display.rotationBadge": "Rotation",
  "level.low": "Low", "level.mid": "Mid", "level.high": "High",
  "day.monday": "Monday", "day.sunday": "Sunday",

  "field.volume": "Volume", "field.timezone": "Time zone", "field.dateFormat": "Date format",
  "field.showWeek": "Show weekday on clock", "field.weekStart": "Week starts on",
  "field.scrollSpeed": "Text scroll speed", "field.lowBatteryAutoSleep": "Sleep on low battery",
  "field.timeFormat": "Time format", "field.city": "City", "field.cityHint": "Search any city; sets coordinates",
  "field.displayInfo": "Show", "field.focusTime": "Focus minutes", "field.relaxTime": "Break minutes",
  "flag.displayTemperature": "Temperature", "flag.displayHumidity": "Humidity",
  "flag.displayPressure": "Pressure", "flag.displayAqi": "Air quality",
  "field.uid": "Account ID", "field.uidHint": "Whose numbers the clock shows: the ID or handle from the profile page",
  "field.token": "Access token", "field.tokenHint": "This platform needs one. It goes straight to the clock; tc002 never saves or shows it",
  "field.tokenPlaceholder": "Paste a token", "field.tokenSend": "Send to clock", "field.tokenSet": "Token on clock",
  "field.tokenSent": "Token sent to the clock",
  "apps.moreSocial": "Also available once switched on: {list}.",
  "apps.off": "switched off", "city.placeholder": "Search a city…", "city.source.open-meteo": "Open-Meteo",
  "city.source.offline": "built-in list (offline)", "city.none": "No matching city",

  "msg.type": "Type", "msg.text": "Text", "msg.alert": "Alert", "msg.message": "Message",
  "msg.messageHint": "English or Chinese. Short text shimmers in place; longer text scrolls.",
  "msg.placeholder": "BUILD OK",
  "fresh.ok": "tc002 screen · updated {ago}", "fresh.stale": "No new data since {ago}: {error}",
  "fresh.never": "No data yet: {error}",
  "led.title": "LED colours", "led.hint": "tc002's own screens on the clock; built-in apps keep their colours",
  "led.match": "Match the interface", "led.classic": "Classic", "led.applied": "LED colours updated",
  "msg.sampleText": "HELLO", "msg.sampleAlert": "DONE", "pal.dialog": "Command palette", "unit.seconds": "s",
  "agent.claude": "Claude Code", "agent.codex": "Codex", "msg.colour": "Colour",
  "msg.colourHint": "Long text scrolls across", "msg.kind": "Kind", "msg.kindHint": "Icon and colour",
  "msg.sent": "Sent to the clock", "msg.plays": "Plays for about {s}s, then clears",
  "kind.done": "Done", "kind.wait": "Wait", "kind.error": "Error",

  "int.agent": "launchd agent dev.tc002.watch", "int.toml": "tc002.toml",
  "int.cli": "Command line", "int.notSet": "not set — run tc002 setup --config",
  "hook.Stop": "Turn finished → DONE", "hook.Notification": "Claude needs you → WAIT",
  "hook.UserPromptSubmit": "You replied → clear",

  "pal.placeholder": "Type a command or search…", "pal.go": "Go to", "pal.actions": "Actions",
  "pal.show": "Show on clock", "pal.prefs": "Preferences", "pal.empty": "No matching command",
  "pal.save": "Save & apply changes", "pal.discard": "Discard changes",
  "pal.apply": "Apply tc002.toml to the clock", "pal.liveOn": "Start live preview on the clock",
  "pal.liveOff": "Stop live preview", "pal.testAlert": "Send a test DONE alert",
  "pal.refresh": "Refresh from the clock", "pal.activity": "Show activity",
  "pal.themeSystem": "Theme: follow system", "pal.themeLight": "Theme: light",
  "pal.themeDark": "Theme: dark", "pal.langEn": "Language: English", "pal.langZh": "Language: 中文",
  "nav.collapse": "Collapse sidebar  [", "nav.expand": "Expand sidebar  [",
  "quick.title": "Quick settings", "quick.brightness": "Brightness", "quick.volume": "Volume",
  "quick.more": "All display & sound settings", "quick.applied": "Applied to the clock",
  "rotation.presets": "Presets", "rotation.presetsHint": "Start from a ready-made rotation; save to apply it.",
  "rotation.slots": "Slots", "preset.loaded": "Preset loaded", "preset.loadedHint": "Save to put it on the clock",
  "preset.focus.name": "Coding focus", "preset.focus.desc": "Claude activity, then today's tokens",
  "preset.developer.name": "Developer desk", "preset.developer.desc": "Claude, tokens, CPU and the clock",
  "preset.agents.name": "AI agents", "preset.agents.desc": "Claude Code and Codex at a glance",
  "preset.ambient.name": "Ambient", "preset.ambient.desc": "Clock and weather, nothing else",
  "preset.clock.name": "Just the clock", "preset.clock.desc": "The built-in clock on its own",
  "preset.desk.name": "Desk", "preset.desk.desc": "Clock, focus timer, progress of the day, world time",
  "preset.calm.name": "Calm", "preset.calm.desc": "Fireplace, clock, moon and Game of Life",
  "ui.search": "Search", "ui.theme": "Theme", "ui.language": "Language", "ui.palette": "Colour",
  "palette.paper": "Paper · vermilion", "palette.matcha": "Matcha · green", "palette.ai": "Ai · indigo",
  "palette.sakura": "Sakura · pink", "palette.kohaku": "Kohaku · amber",
  "ago.s": "{n}s ago", "ago.m": "{n} min ago", "ago.h": "{n} h ago", "ago.now": "just now",
  "err.load": "Could not load: {msg}",
};

const zh = {
  "nav.clock": "时钟", "nav.send": "发送", "nav.system": "系统",
  "page.overview": "总览", "page.rotation": "轮播", "page.builtins": "预设应用",
  "page.display": "显示与声音", "page.apps": "应用设置", "page.messages": "消息",
  "page.integrations": "集成",
  "desc.overview": "时钟正在做什么，以及它是否与 tc002.toml 一致。",
  "desc.rotation": "时钟依次循环显示的画面。拖动调整顺序，或从预设开始。",
  "desc.builtins": "保留在时钟上的预设应用。关闭的应用不会在设备上出现。",
  "desc.display": "时钟的亮度、音量、时间和日期。保存到 tc002.toml 并同步到时钟。",
  "desc.apps": "tc002 画面和时钟预设应用的选项。账号和 API 密钥保留在 Ulanzi Studio 中。",
  "desc.messages": "发送一条临时消息，播放完自动清除。",
  "desc.integrations": "tc002 与这台 Mac 的连接方式。",

  "status.loading": "加载中…", "status.synced": "已同步", "status.dirty": "{n} 项未保存",
  "status.saving": "正在保存并应用…", "status.applied": "已应用到时钟",
  "status.savedOffline": "已保存，时钟离线", "status.error": "保存失败",
  "status.drift": "时钟与 tc002.toml 不一致", "status.live": "正在时钟上实时预览",
  "status.liveStarting": "正在发送到时钟…", "activity.title": "操作记录",
  "activity.empty": "本次会话还没有操作。", "activity.save": "保存并应用",
  "activity.live": "实时预览", "activity.liveStop": "实时预览已结束",
  "activity.show": "在时钟上显示", "activity.message": "已发送消息",
  "activity.apply": "应用 tc002.toml", "activity.changes": "时钟上 {n} 项改动",
  "activity.noChanges": "时钟已是最新",

  "save.unsaved": "有未保存的更改", "save.discard": "放弃", "save.save": "保存并应用",
  "save.savedApplied": "已保存并应用", "save.serviceReloaded": "后台服务已重载",
  "save.saved": "已保存到 tc002.toml",

  "preview.title": "预览", "preview.live": "在时钟上实时预览",
  "preview.liveHint": "保存前就在硬件上播放改动。关闭后恢复为 tc002.toml 的设置。",
  "preview.liveOn": "实时预览中 · 轮播已暂停", "preview.approx": "近似模拟时钟自带应用",
  "preview.sample": "示例数据", "preview.rotation": "轮播", "preview.play": "播放",
  "preview.pause": "暂停", "preview.message": "消息草稿", "preview.offline": "时钟离线，无法实时预览",

  "row.clock": "时钟", "row.service": "后台服务", "row.hooks": "Claude Code hook",
  "row.sync": "时钟与 tc002.toml 一致", "row.lastEvent": "最近事件：{kind}，{ago}",
  "row.noEvent": "暂无事件", "row.everythingSynced": "全部已同步",
  "row.differs": "不一致：{list}", "row.customApps": "时钟上的自定义应用",
  "row.customAppsHint": "由 tc002 或其他工具推送", "row.none": "无",
  "badge.online": "在线", "badge.offline": "离线", "badge.running": "运行中",
  "badge.stopped": "已停止", "badge.inSync": "已同步", "badge.installed": "已安装",
  "badge.missing": "缺失", "badge.hooks": "已安装 {n}/3",
  "btn.refresh": "刷新", "btn.applyNow": "立即应用", "btn.retry": "重试",
  "btn.addSlot": "添加", "btn.send": "发送到时钟", "btn.showNow": "立即在时钟上显示",
  "btn.remove": "移除", "btn.clear": "清除",
  "section.status": "状态", "section.device": "设备", "section.behaviour": "行为",
  "section.brightness": "亮度", "section.general": "通用", "section.compose": "编辑",
  "section.service": "后台服务", "section.hooks": "Claude Code hook",
  "section.config": "配置", "section.preferences": "偏好",
  "fact.ip": "IP", "fact.wifi": "Wi-Fi", "fact.firmware": "固件", "fact.mcu": "MCU",
  "fact.mac": "MAC", "fact.serial": "序列号",

  "rotation.screen": "tc002 画面", "rotation.builtin": "预设应用",
  "rotation.empty": "没有项目：由时钟自带的轮播决定显示内容。",
  "rotation.cycle": "一轮 {s} 秒", "rotation.screens": "画面",
  "rotation.builtins": "预设应用", "rotation.nothing": "没有可添加的项目",
  "rotation.takeover": "提醒优先显示",
  "rotation.takeoverHint": "有会话在等你时立即占用时钟，直到你回复；完成的会话会短暂显示 DONE",
  "rotation.screenToggle": "{name}画面", "rotation.screenHint": "在后台服务中运行这个画面",
  "rotation.drag": "拖动排序", "rotation.seconds": "秒",

  "builtins.onNow": "时钟上已开启", "builtins.offNow": "时钟上已关闭",
  "builtins.linked": "已在 Ulanzi Studio 绑定账号", "builtins.inRotation": "在轮播中",
  "builtins.cat.tools": "工具", "builtins.cat.social": "社媒", "builtins.cat.calendar": "日历",

  "display.fromClock": "时钟当前值", "display.inToml": "已写入 tc002.toml",
  "display.pending": "已写入 tc002.toml · 尚未同步到时钟",
  "display.level": "当前档位", "display.levelPercent": "{level}档亮度",
  "display.percentHint": "百分比；低 < 中 < 高", "display.carousel": "设备自带轮播",
  "display.carouselOff": "已关闭 — 由 tc002 轮播控制屏幕",
  "display.carouselDevice": "由时钟决定（没有轮播）", "display.rotationBadge": "轮播",
  "level.low": "低", "level.mid": "中", "level.high": "高",
  "day.monday": "周一", "day.sunday": "周日",

  "field.volume": "音量", "field.timezone": "时区", "field.dateFormat": "日期格式",
  "field.showWeek": "时钟显示星期", "field.weekStart": "每周起始日",
  "field.scrollSpeed": "文字滚动速度", "field.lowBatteryAutoSleep": "低电量自动休眠",
  "field.timeFormat": "时间格式", "field.city": "城市", "field.cityHint": "搜索任意城市，自动填入经纬度",
  "field.displayInfo": "显示", "field.focusTime": "专注时长（分钟）", "field.relaxTime": "休息时长（分钟）",
  "flag.displayTemperature": "温度", "flag.displayHumidity": "湿度",
  "flag.displayPressure": "气压", "flag.displayAqi": "空气质量",
  "field.uid": "账号 ID", "field.uidHint": "时钟显示谁的数据：主页上的 ID 或用户名",
  "field.token": "访问令牌", "field.tokenHint": "该平台需要令牌。它直接发送到时钟，tc002 不会保存或显示",
  "field.tokenPlaceholder": "粘贴令牌", "field.tokenSend": "发送到时钟", "field.tokenSet": "时钟已有令牌",
  "field.tokenSent": "令牌已发送到时钟",
  "apps.moreSocial": "开启后还可以设置：{list}。",
  "apps.off": "已关闭", "city.placeholder": "搜索城市…", "city.source.open-meteo": "Open-Meteo",
  "city.source.offline": "内置列表（离线）", "city.none": "没有匹配的城市",

  "msg.type": "类型", "msg.text": "文字", "msg.alert": "提醒", "msg.message": "内容",
  "msg.messageHint": "中英文均可。短文字原地闪光，长文字会滚动。",
  "msg.placeholder": "构建完成",
  "fresh.ok": "tc002 画面 · {ago}更新", "fresh.stale": "{ago}起没有新数据：{error}",
  "fresh.never": "还没有数据：{error}",
  "led.title": "LED 配色", "led.hint": "作用于时钟上 tc002 自己的画面，预设应用保持原色",
  "led.match": "跟随界面配色", "led.classic": "经典", "led.applied": "LED 配色已更新",
  "msg.sampleText": "你好", "msg.sampleAlert": "完成", "pal.dialog": "命令面板", "unit.seconds": "秒",
  "agent.claude": "Claude Code", "agent.codex": "Codex", "msg.colour": "颜色",
  "msg.colourHint": "长文字会滚动显示", "msg.kind": "种类", "msg.kindHint": "图标和颜色",
  "msg.sent": "已发送到时钟", "msg.plays": "播放约 {s} 秒后自动清除",
  "kind.done": "完成", "kind.wait": "等待", "kind.error": "错误",

  "int.agent": "launchd 服务 dev.tc002.watch", "int.toml": "tc002.toml",
  "int.cli": "命令行", "int.notSet": "未设置 — 运行 tc002 setup --config",
  "hook.Stop": "回答结束 → DONE", "hook.Notification": "Claude 需要你 → WAIT",
  "hook.UserPromptSubmit": "你已回复 → 清除",

  "pal.placeholder": "输入命令或搜索…", "pal.go": "前往", "pal.actions": "操作",
  "pal.show": "在时钟上显示", "pal.prefs": "偏好", "pal.empty": "没有匹配的命令",
  "pal.save": "保存并应用更改", "pal.discard": "放弃更改",
  "pal.apply": "把 tc002.toml 应用到时钟", "pal.liveOn": "开始在时钟上实时预览",
  "pal.liveOff": "停止实时预览", "pal.testAlert": "发送测试 DONE 提醒",
  "pal.refresh": "从时钟刷新", "pal.activity": "查看操作记录",
  "pal.themeSystem": "主题：跟随系统", "pal.themeLight": "主题：浅色",
  "pal.themeDark": "主题：深色", "pal.langEn": "语言：English", "pal.langZh": "语言：中文",
  "nav.collapse": "收起侧栏  [", "nav.expand": "展开侧栏  [",
  "quick.title": "快捷设置", "quick.brightness": "亮度", "quick.volume": "音量",
  "quick.more": "全部显示与声音设置", "quick.applied": "已应用到时钟",
  "rotation.presets": "预设", "rotation.presetsHint": "从现成的轮播开始；保存后生效。",
  "rotation.slots": "轮播项", "preset.loaded": "已载入预设", "preset.loadedHint": "保存后应用到时钟",
  "preset.focus.name": "专注编码", "preset.focus.desc": "Claude 活动，然后是今天的 token",
  "preset.developer.name": "开发者桌面", "preset.developer.desc": "Claude、token、CPU 和时钟",
  "preset.agents.name": "AI 代理", "preset.agents.desc": "一眼看清 Claude Code 和 Codex",
  "preset.ambient.name": "氛围", "preset.ambient.desc": "只有时钟和天气",
  "preset.clock.name": "只看时钟", "preset.clock.desc": "只显示自带时钟",
  "preset.desk.name": "书桌", "preset.desk.desc": "时钟、专注计时、今日进度、世界时间",
  "preset.calm.name": "放松", "preset.calm.desc": "壁炉、时钟、月相和生命游戏",
  "ui.search": "搜索", "ui.theme": "主题", "ui.language": "语言", "ui.palette": "配色",
  "palette.paper": "和纸 · 朱", "palette.matcha": "抹茶 · 绿", "palette.ai": "藍 · 靛蓝",
  "palette.sakura": "樱 · 粉", "palette.kohaku": "琥珀 · 金",
  "ago.s": "{n} 秒前", "ago.m": "{n} 分钟前", "ago.h": "{n} 小时前", "ago.now": "刚刚",
  "err.load": "无法加载：{msg}",
};

// Built-in app and screen names.
const names = {
  en: { claude: "Sessions", sys: "System", usage: "Plan limits", focus: "Focus timer",
    progress: "Day progress", countdown: "Countdown", worldclock: "World clock", sun: "Sunrise & sunset",
    moon: "Moon", life: "Game of Life", fire: "Fireplace", agenda: "Calendar", github: "GitHub",
    nowplaying: "Now playing", air: "Air quality", crypto: "Crypto", stocks: "Stocks",
    hackernews: "Hacker News", home: "Home Assistant", codex: "Codex", clock: "Clock", weather: "Weather", busy: "Busy light",
    scoreboard: "Scoreboard", tomato: "Pomodoro", stopwatch: "Stopwatch", battery: "Battery",
    soundlight: "Sound light", ipshow: "IP address", xhs: "Xiaohongshu", douyin: "Douyin",
    bilibili: "Bilibili", weibo: "Weibo", youtube: "YouTube", instagram: "Instagram",
    facebook: "Facebook", tiktok: "TikTok", x: "X", feishu: "Feishu", dingding: "DingTalk",
    wecom: "WeCom", google: "Google Calendar", icloud: "iCloud", outlook: "Outlook" },
  zh: { claude: "会话", sys: "系统", usage: "用量额度", focus: "专注计时",
    progress: "今日进度", countdown: "倒数日", worldclock: "世界时钟", sun: "日出日落",
    moon: "月相", life: "生命游戏", fire: "壁炉", agenda: "日历", github: "GitHub",
    nowplaying: "正在播放", air: "空气质量", crypto: "加密货币", stocks: "股票",
    hackernews: "Hacker News", home: "Home Assistant", codex: "Codex", clock: "时钟", weather: "天气", busy: "忙碌灯",
    scoreboard: "计分板", tomato: "番茄钟", stopwatch: "秒表", battery: "电量",
    soundlight: "拾音灯", ipshow: "IP 显示", xhs: "小红书", douyin: "抖音",
    bilibili: "哔哩哔哩", weibo: "微博", youtube: "YouTube", instagram: "Instagram",
    facebook: "Facebook", tiktok: "TikTok", x: "X", feishu: "飞书", dingding: "钉钉",
    wecom: "企业微信", google: "Google 日历", icloud: "iCloud 日历", outlook: "Outlook" },
};

const DICTS = {
  en: { ...en, ...agents.en, ...errors.en },
  zh: { ...zh, ...agents.zh, ...errors.zh },
};
let current = "en";

export function setLang(lang) {
  current = DICTS[lang] ? lang : "en";
  document.documentElement.lang = current === "zh" ? "zh-CN" : "en";
}

export const lang = () => current;

export function t(key, vars = {}) {
  const text = DICTS[current][key] ?? DICTS.en[key] ?? key;
  return text.replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? "");
}

export const appName = (key) => names[current][key] ?? names.en[key] ?? key;

// "1 h 42 min" until a Unix time; null when it has passed or is unknown.
export function until(unix) {
  const left = Math.round(unix - Date.now() / 1000);
  if (!unix || left <= 0) return null;
  const h = Math.floor(left / 3600), m = Math.round((left % 3600) / 60);
  return h ? t("ago.until.h", { h, m }) : t("ago.until.m", { m: Math.max(1, m) });
}

export function ago(seconds) {
  if (seconds < 5) return t("ago.now");
  if (seconds < 60) return t("ago.s", { n: seconds });
  if (seconds < 3600) return t("ago.m", { n: Math.round(seconds / 60) });
  return t("ago.h", { n: Math.round(seconds / 3600) });
}
