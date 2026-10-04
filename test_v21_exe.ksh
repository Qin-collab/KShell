echo === 1. plugin list ===
plugin list
echo === 2. 官方示例插件执行 ===
hello 打包测试
pwgen 1 12
uuid
sysinfo --json
echo === 3. plugin new 落盘位置 ===
plugin new packagedemo
echo === 4. 加载并执行新插件 ===
plugin reload packagedemo
packagedemo Test
echo === 5. plugin dirs ===
plugin dirs
echo === done ===
