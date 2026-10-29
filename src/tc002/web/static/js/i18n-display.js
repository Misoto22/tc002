// Strings for what the clock shows: the display mode, the screen library with a line on
// each screen, built-in app settings and the games. Merged into the dictionaries by i18n.js.

export const en = {
  "page.rotation": "On the clock", "page.builtins": "Built-in apps",
  "desc.rotation": "What the clock shows: several screens in turn, or one screen all the time.",
  "desc.builtins": "The clock's own apps. Keep the ones you want and set them up here; the rest are switched off on the device.",

  "mode.title": "How the clock shows them",
  "mode.cycle": "Rotate", "mode.cycleHint": "Step through the list below, each for its own time",
  "mode.single": "Show one", "mode.singleHint": "Hold one screen until you change it",
  "mode.nowCycle": "{n} screens in turn · one round takes {s}s",
  "mode.nowSingle": "Always shows {name}",
  "mode.nowEmpty": "Nothing chosen: the clock's own carousel decides",
  "mode.alertsNote": "Alerts still interrupt either way while “Alerts take over” is on.",
  "mode.pick": "Pick the screen to hold",
  "mode.pickEmpty": "Switch a screen on below, or keep a built-in app, to choose it here.",
  "mode.templates": "Start from a template", "mode.templatesHint": "Replaces the list; save to apply",

  "library.title": "Screens", "library.hint": "tc002 draws these on your Mac. Switch one on to use it.",
  "library.on": "On", "library.add": "Add to rotation", "library.inRotation": "In the rotation",
  "library.options": "Options", "library.preview": "Preview on the left",
  "library.networked": "Uses the internet", "library.setup": "Needs a connection",

  "behaviour.takeoverHint": "When a Claude Code session waits for you, the clock jumps to it until you answer",
  "behaviour.example": "Example",

  "builtins.settings": "Settings", "builtins.offHint": "Switch on to set it up",
  "builtins.account": "Account", "builtins.inUse": "Used by the rotation",

  "overview.now": "On the clock now", "overview.edit": "Change",
  "overview.wizard": "Setup wizard", "overview.wizardHint": "Replace the clock or set this one up again",

  "quick.open": "Brightness & volume",
  "play.preview": "Preview", "play.start": "Play",

  "screen.claude": "How many Claude Code sessions are working, waiting or done",
  "screen.usage": "Claude Code and Codex plan limits, 5-hour and weekly",
  "screen.sys": "CPU over the last minute, and memory",
  "screen.focus": "A work-and-break timer counting down",
  "screen.progress": "How much of the day, week and year has gone",
  "screen.countdown": "Days to a date you name",
  "screen.worldclock": "The time in two places",
  "screen.sun": "Today's sunrise and sunset where your weather city is",
  "screen.moon": "Tonight's moon phase",
  "screen.life": "Conway's Game of Life, slowly evolving",
  "screen.fire": "A calm fireplace",
  "screen.agenda": "Your next event, from a calendar link",
  "screen.github": "Reviews, pull requests and notifications waiting on GitHub",
  "screen.nowplaying": "What Music or Spotify is playing",
  "screen.air": "Air quality where your weather city is",
  "screen.crypto": "Two coins and their 24-hour change",
  "screen.stocks": "A stock's price and its day",
  "screen.hackernews": "The top Hacker News story",
  "screen.home": "Two Home Assistant sensors",
};

export const zh = {
  "page.rotation": "显示内容", "page.builtins": "内置应用",
  "desc.rotation": "时钟显示什么：几个画面轮流显示，或一直显示一个。",
  "desc.builtins": "时钟自带的应用。保留需要的并在这里设置，其余的会在设备上关闭。",

  "mode.title": "显示方式",
  "mode.cycle": "轮播", "mode.cycleHint": "按下面的顺序循环，每个画面显示各自的时长",
  "mode.single": "固定显示", "mode.singleHint": "一直显示一个画面，直到你更改",
  "mode.nowCycle": "{n} 个画面轮流显示 · 一轮 {s} 秒",
  "mode.nowSingle": "一直显示{name}",
  "mode.nowEmpty": "还没有选择：由时钟自带的轮播决定",
  "mode.alertsNote": "无论哪种方式，开启“提醒优先显示”时提醒都会插入。",
  "mode.pick": "选择要固定显示的画面",
  "mode.pickEmpty": "先在下方开启一个画面，或保留一个内置应用，才能在这里选择。",
  "mode.templates": "从模板开始", "mode.templatesHint": "会替换当前列表；保存后生效",

  "library.title": "画面", "library.hint": "这些画面由 tc002 在你的 Mac 上绘制。开启后即可使用。",
  "library.on": "开启", "library.add": "加入轮播", "library.inRotation": "已在轮播中",
  "library.options": "选项", "library.preview": "左上角可预览",
  "library.networked": "需要联网", "library.setup": "需要先连接服务",

  "behaviour.takeoverHint": "Claude Code 会话在等你时，时钟立即切过去，直到你回复",
  "behaviour.example": "示例",

  "builtins.settings": "设置", "builtins.offHint": "开启后可以设置",
  "builtins.account": "账号", "builtins.inUse": "轮播正在使用",

  "overview.now": "时钟正在显示", "overview.edit": "更改",
  "overview.wizard": "设置向导", "overview.wizardHint": "更换时钟，或重新设置这台",

  "quick.open": "亮度与音量",
  "play.preview": "预览", "play.start": "开始",

  "screen.claude": "Claude Code 会话：运行中、等你回复、已完成各有几个",
  "screen.usage": "Claude Code 和 Codex 的 5 小时与每周额度",
  "screen.sys": "最近一分钟的 CPU 曲线和内存",
  "screen.focus": "工作与休息交替的倒计时",
  "screen.progress": "今天、本周、今年过去了多少",
  "screen.countdown": "距离某个日期还有几天",
  "screen.worldclock": "两个地方的当地时间",
  "screen.sun": "天气城市今天的日出和日落",
  "screen.moon": "今晚的月相",
  "screen.life": "缓慢演化的康威生命游戏",
  "screen.fire": "安静的壁炉火焰",
  "screen.agenda": "日历链接里的下一个日程",
  "screen.github": "GitHub 上等你处理的评审、PR 和通知",
  "screen.nowplaying": "音乐或 Spotify 正在播放的歌",
  "screen.air": "天气城市的空气质量",
  "screen.crypto": "两种币的价格和 24 小时涨跌",
  "screen.stocks": "一只股票的价格和当日走势",
  "screen.hackernews": "Hacker News 头条",
  "screen.home": "Home Assistant 的两个传感器",
};
