// UI strings in English and Chinese. t("key", {var}) looks up the current language and
// falls back to English, then to the key itself, so a missing string is visible, not blank.

const en = {
  "nav.clock": "Clock", "nav.send": "Send", "nav.system": "System",
  "page.overview": "Overview", "page.playlist": "Playlist", "page.builtins": "Built-in apps",
  "page.display": "Display", "page.apps": "App settings", "page.messages": "Messages",
  "page.integrations": "Integrations",
  "desc.overview": "What your clock is doing and whether it matches tc002.toml.",
  "desc.playlist": "What the clock shows, in order. Drag to reorder.",
  "desc.builtins": "Apps that stay on the clock. Everything switched off is hidden from the device.",
  "desc.display": "Clock-wide settings, saved to tc002.toml and applied to the clock.",
  "desc.apps": "Options of the built-in apps. Accounts and API keys stay in Ulanzi Studio.",
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
  "preview.liveOn": "Live · playlist paused", "preview.approx": "Approximation of the clock's own app",
  "preview.sample": "sample data", "preview.playlist": "Playlist", "preview.play": "Play",
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

  "playlist.screen": "tc002 screen", "playlist.builtin": "Built-in app",
  "playlist.empty": "No slots: the clock's own carousel decides what to show.",
  "playlist.cycle": "One cycle: {s}s", "playlist.screens": "Screens",
  "playlist.builtins": "Built-in apps", "playlist.nothing": "Nothing to add",
  "playlist.takeover": "Alerts take over",
  "playlist.takeoverHint": "DONE and WAIT from Claude Code jump to the Claude screen at once",
  "playlist.screenToggle": "{name} screen", "playlist.screenHint": "Run this screen in the background service",
  "playlist.drag": "Drag to reorder", "playlist.seconds": "seconds",

  "builtins.onNow": "On the clock now", "builtins.offNow": "Off on the clock",
  "builtins.linked": "account linked in Ulanzi Studio", "builtins.inPlaylist": "in the playlist",
  "builtins.cat.tools": "Tools", "builtins.cat.social": "Social", "builtins.cat.calendar": "Calendar",

  "display.fromClock": "Clock's own value", "display.inToml": "Set in tc002.toml",
  "display.pending": "Set in tc002.toml · not yet on the clock",
  "display.level": "Active level", "display.levelPercent": "{level} level",
  "display.percentHint": "Percent; low < mid < high", "display.carousel": "Device carousel",
  "display.carouselOff": "Off — the tc002 playlist drives the screen",
  "display.carouselDevice": "Set by the clock (no playlist)", "display.playlistBadge": "Playlist",
  "level.low": "Low", "level.mid": "Mid", "level.high": "High",
  "day.monday": "Monday", "day.sunday": "Sunday",

  "field.volume": "Volume", "field.timezone": "Time zone", "field.dateFormat": "Date format",
  "field.showWeek": "Show weekday on clock", "field.weekStart": "Week starts on",
  "field.scrollSpeed": "Text scroll speed", "field.lowBatteryAutoSleep": "Sleep on low battery",
  "field.timeFormat": "Time format", "field.city": "City", "field.cityHint": "Search any city; sets coordinates",
  "field.displayInfo": "Show", "field.focusTime": "Focus minutes", "field.relaxTime": "Break minutes",
  "flag.displayTemperature": "Temperature", "flag.displayHumidity": "Humidity",
  "flag.displayPressure": "Pressure", "flag.displayAqi": "Air quality",
  "apps.off": "switched off", "city.placeholder": "Search a city…", "city.source.open-meteo": "Open-Meteo",
  "city.source.offline": "built-in list (offline)", "city.none": "No matching city",

  "msg.type": "Type", "msg.text": "Text", "msg.alert": "Alert", "msg.message": "Message",
  "msg.messageHint": "ASCII, shown upper case", "msg.colour": "Colour",
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
  "ui.search": "Search", "ui.theme": "Theme", "ui.language": "Language",
  "ago.s": "{n}s ago", "ago.m": "{n} min ago", "ago.h": "{n} h ago", "ago.now": "just now",
  "err.load": "Could not load: {msg}",
};

const zh = {
  "nav.clock": "时钟", "nav.send": "发送", "nav.system": "系统",
  "page.overview": "总览", "page.playlist": "播放列表", "page.builtins": "预设应用",
  "page.display": "显示", "page.apps": "应用设置", "page.messages": "消息",
  "page.integrations": "集成",
  "desc.overview": "时钟正在做什么，以及它是否与 tc002.toml 一致。",
  "desc.playlist": "时钟按顺序显示的内容。拖动即可调整顺序。",
  "desc.builtins": "保留在时钟上的预设应用。关闭的应用不会在设备上出现。",
  "desc.display": "全局设置，保存到 tc002.toml 并同步到时钟。",
  "desc.apps": "预设应用的选项。账号和 API 密钥仍由 Ulanzi Studio 管理。",
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
  "preview.liveOn": "实时预览中 · 播放列表已暂停", "preview.approx": "近似模拟时钟自带应用",
  "preview.sample": "示例数据", "preview.playlist": "播放列表", "preview.play": "播放",
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

  "playlist.screen": "tc002 画面", "playlist.builtin": "预设应用",
  "playlist.empty": "没有项目：由时钟自带的轮播决定显示内容。",
  "playlist.cycle": "一轮 {s} 秒", "playlist.screens": "画面",
  "playlist.builtins": "预设应用", "playlist.nothing": "没有可添加的项目",
  "playlist.takeover": "提醒优先显示",
  "playlist.takeoverHint": "Claude Code 的 DONE 和 WAIT 会立即切到 Claude 画面",
  "playlist.screenToggle": "{name}画面", "playlist.screenHint": "在后台服务中运行这个画面",
  "playlist.drag": "拖动排序", "playlist.seconds": "秒",

  "builtins.onNow": "时钟上已开启", "builtins.offNow": "时钟上已关闭",
  "builtins.linked": "已在 Ulanzi Studio 绑定账号", "builtins.inPlaylist": "在播放列表中",
  "builtins.cat.tools": "工具", "builtins.cat.social": "社媒", "builtins.cat.calendar": "日历",

  "display.fromClock": "时钟当前值", "display.inToml": "已写入 tc002.toml",
  "display.pending": "已写入 tc002.toml · 尚未同步到时钟",
  "display.level": "当前档位", "display.levelPercent": "{level}档亮度",
  "display.percentHint": "百分比；低 < 中 < 高", "display.carousel": "设备自带轮播",
  "display.carouselOff": "已关闭 — 由 tc002 播放列表控制屏幕",
  "display.carouselDevice": "由时钟决定（没有播放列表）", "display.playlistBadge": "播放列表",
  "level.low": "低", "level.mid": "中", "level.high": "高",
  "day.monday": "周一", "day.sunday": "周日",

  "field.volume": "音量", "field.timezone": "时区", "field.dateFormat": "日期格式",
  "field.showWeek": "时钟显示星期", "field.weekStart": "每周起始日",
  "field.scrollSpeed": "文字滚动速度", "field.lowBatteryAutoSleep": "低电量自动休眠",
  "field.timeFormat": "时间格式", "field.city": "城市", "field.cityHint": "搜索任意城市，自动填入经纬度",
  "field.displayInfo": "显示", "field.focusTime": "专注时长（分钟）", "field.relaxTime": "休息时长（分钟）",
  "flag.displayTemperature": "温度", "flag.displayHumidity": "湿度",
  "flag.displayPressure": "气压", "flag.displayAqi": "空气质量",
  "apps.off": "已关闭", "city.placeholder": "搜索城市…", "city.source.open-meteo": "Open-Meteo",
  "city.source.offline": "内置列表（离线）", "city.none": "没有匹配的城市",

  "msg.type": "类型", "msg.text": "文字", "msg.alert": "提醒", "msg.message": "内容",
  "msg.messageHint": "仅 ASCII，显示为大写", "msg.colour": "颜色",
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
  "ui.search": "搜索", "ui.theme": "主题", "ui.language": "语言",
  "ago.s": "{n} 秒前", "ago.m": "{n} 分钟前", "ago.h": "{n} 小时前", "ago.now": "刚刚",
  "err.load": "无法加载：{msg}",
};

// Built-in app and screen names.
const names = {
  en: { claude: "Claude Code", sys: "System", clock: "Clock", weather: "Weather", busy: "Busy light",
    scoreboard: "Scoreboard", tomato: "Pomodoro", stopwatch: "Stopwatch", battery: "Battery",
    soundlight: "Sound light", ipshow: "IP address", xhs: "Xiaohongshu", douyin: "Douyin",
    bilibili: "Bilibili", weibo: "Weibo", youtube: "YouTube", instagram: "Instagram",
    facebook: "Facebook", tiktok: "TikTok", x: "X", feishu: "Feishu", dingding: "DingTalk",
    wecom: "WeCom", google: "Google Calendar", icloud: "iCloud", outlook: "Outlook" },
  zh: { claude: "Claude Code", sys: "系统", clock: "时钟", weather: "天气", busy: "忙碌灯",
    scoreboard: "计分板", tomato: "番茄钟", stopwatch: "秒表", battery: "电量",
    soundlight: "拾音灯", ipshow: "IP 显示", xhs: "小红书", douyin: "抖音",
    bilibili: "哔哩哔哩", weibo: "微博", youtube: "YouTube", instagram: "Instagram",
    facebook: "Facebook", tiktok: "TikTok", x: "X", feishu: "飞书", dingding: "钉钉",
    wecom: "企业微信", google: "Google 日历", icloud: "iCloud 日历", outlook: "Outlook" },
};

const DICTS = { en, zh };
let current = "en";

export function setLang(lang) {
  current = DICTS[lang] ? lang : "en";
  document.documentElement.lang = current === "zh" ? "zh-CN" : "en";
}

export const lang = () => current;

export function t(key, vars = {}) {
  const text = DICTS[current][key] ?? en[key] ?? key;
  return text.replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? "");
}

export const appName = (key) => names[current][key] ?? names.en[key] ?? key;

export function ago(seconds) {
  if (seconds < 5) return t("ago.now");
  if (seconds < 60) return t("ago.s", { n: seconds });
  if (seconds < 3600) return t("ago.m", { n: Math.round(seconds / 60) });
  return t("ago.h", { n: Math.round(seconds / 3600) });
}
