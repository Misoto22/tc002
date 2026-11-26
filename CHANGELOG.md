# Changelog

## [0.2.0](https://github.com/Misoto22/tc002/compare/v0.1.0...v0.2.0) (2026-11-26)


### Features

* **app:** share one application layer and serve it over MCP ([#26](https://github.com/Misoto22/tc002/issues/26)) ([b0d4fee](https://github.com/Misoto22/tc002/commit/b0d4fee85b62256c96f0eefdefcacd6ba8499870))
* **app:** show sessions and plan limits; redesign the UI ([#6](https://github.com/Misoto22/tc002/issues/6)) ([5351239](https://github.com/Misoto22/tc002/commit/535123913e5a0fa99791c589353506f46e19237c))
* **clock:** add LED themes, stale-data states and social accounts ([#9](https://github.com/Misoto22/tc002/issues/9)) ([cb6971f](https://github.com/Misoto22/tc002/commit/cb6971f7384576a410d7a6ffb31b9ad2f8d5549e))
* **connections:** add screens from services, with secrets in the Keychain ([#13](https://github.com/Misoto22/tc002/issues/13)) ([654840f](https://github.com/Misoto22/tc002/commit/654840f0f442300e2ace8c94daa4a9186c07180b))
* **display:** let the clock follow this Mac's time zone ([#27](https://github.com/Misoto22/tc002/issues/27)) ([d00598d](https://github.com/Misoto22/tc002/commit/d00598d920bbe7b35d7bb9d256795b1d6f347991))
* **display:** turn the screen fully dark at night or on demand ([#22](https://github.com/Misoto22/tc002/issues/22)) ([7da3fe5](https://github.com/Misoto22/tc002/commit/7da3fe53f0a08693d513c80147b1936908052a96))
* **games:** play Breakout, Snake and Pong on the clock ([#12](https://github.com/Misoto22/tc002/issues/12)) ([47d9c0e](https://github.com/Misoto22/tc002/commit/47d9c0ea3be8374c4af7cf0121f7a4b063a974e8))
* **screens:** add eight screens that need no account or API ([#11](https://github.com/Misoto22/tc002/issues/11)) ([39d8c72](https://github.com/Misoto22/tc002/commit/39d8c72c6f1fc08be21688862f409ed1c971aeac))
* **setup:** take a clock from its box to a working setup ([#10](https://github.com/Misoto22/tc002/issues/10)) ([04ed345](https://github.com/Misoto22/tc002/commit/04ed345b3a339a9272b1befb91fcaefb9497e746))
* **ui:** add a local settings UI with drag-and-drop playlist ([#2](https://github.com/Misoto22/tc002/issues/2)) ([0aa35b5](https://github.com/Misoto22/tc002/commit/0aa35b5fdb6ac3d847817f2b98272c09729260fa))
* **ui:** add colour themes and smoother motion ([#7](https://github.com/Misoto22/tc002/issues/7)) ([ba2d3d4](https://github.com/Misoto22/tc002/commit/ba2d3d4967db4de9a6fc03e632ba812c1dc9e42b))
* **ui:** add token usage, rotation presets, quick settings and a new layout ([#5](https://github.com/Misoto22/tc002/issues/5)) ([ef60e65](https://github.com/Misoto22/tc002/commit/ef60e6541a6055e2e476bb3953838c2b0b5e4760))
* **ui:** give each screen and app its own page with live data ([#16](https://github.com/Misoto22/tc002/issues/16)) ([a9ab6e7](https://github.com/Misoto22/tc002/commit/a9ab6e728cfec8fc03d555a680fec01879b1a329))
* **ui:** show every choice as a picture and add a show-one mode ([#15](https://github.com/Misoto22/tc002/issues/15)) ([6465287](https://github.com/Misoto22/tc002/commit/646528745fea3a73dbf246f035b48b1c36223045))
* **usage:** show Gemini's plan limits, and each agent's usage on Integrations ([#29](https://github.com/Misoto22/tc002/issues/29)) ([f2461c5](https://github.com/Misoto22/tc002/commit/f2461c587cc8d6af18a8c779a56acd6b6167e43b))


### Bug Fixes

* **clock:** report built-in apps the firmware hides instead of failing quietly ([#28](https://github.com/Misoto22/tc002/issues/28)) ([a23efd9](https://github.com/Misoto22/tc002/commit/a23efd97f654299d8145ca164fcf1aa38540c320))
* keep screen threads alive, refuse stale saves, stop fast when the clock is off ([#24](https://github.com/Misoto22/tc002/issues/24)) ([7395f6e](https://github.com/Misoto22/tc002/commit/7395f6e4474e98d728cb30d40022961be6761662))
* **service:** find gh where the shell finds it ([#17](https://github.com/Misoto22/tc002/issues/17)) ([4ab4396](https://github.com/Misoto22/tc002/commit/4ab4396b2dffaf3c18b08ba0a18982e8d825bfef))
* **service:** skip version-manager shims that fail outside a project ([#18](https://github.com/Misoto22/tc002/issues/18)) ([c021bdb](https://github.com/Misoto22/tc002/commit/c021bdb48201621f02d1c2c3f89c4eecaca2636b))
* **ui:** align rows, buttons and tokens to one design system ([#19](https://github.com/Misoto22/tc002/issues/19)) ([f5608ce](https://github.com/Misoto22/tc002/commit/f5608ce0c4bdcf70a43b6a611bcf691a586fc3b1))
* **ui:** fold repeated toasts into one and let each be closed ([#25](https://github.com/Misoto22/tc002/issues/25)) ([1fa51e8](https://github.com/Misoto22/tc002/commit/1fa51e8eec4537d36f5b000ab3922b2c2c21cbaf))
* **ui:** keep working when the console restarts under an open page ([#23](https://github.com/Misoto22/tc002/issues/23)) ([b943e45](https://github.com/Misoto22/tc002/commit/b943e45e0cd46712b15538e8d6b03580da570305))
* **ui:** show Chinese messages, the real Codex mark and drop hardcoded values ([#8](https://github.com/Misoto22/tc002/issues/8)) ([90e8453](https://github.com/Misoto22/tc002/commit/90e8453cc33b7afbdb68d6953c404b9870ea50db))

## 0.1.0 (2026-10-29)


### Features

* add tc002 pixel clock screens, playlist and Claude hooks ([54b6751](https://github.com/Misoto22/tc002/commit/54b6751d705e8c06ab7130f46e41e394ef45c3b6))
