# KShell 2.1 插件系统端到端测试
echo === 1. plugin list ===
plugin list
echo === 2. plugin info hello ===
plugin info hello
echo === 3. 内置示例插件 hello ===
hello KShell -v
echo === 4. 别名命令 greet ===
greet 世界
echo === 5. pwgen 生成密码 ===
pwgen 2 16
echo === 6. uuid ===
uuid
echo === 7. 密码强度 ===
passwd-strength A1b2C3d4!@#$
echo === 8. sysinfo ===
sysinfo
echo === 9. 修改插件配置 ===
plugin config hello greeting=Hi
hello KShell
echo === 10. 恢复配置 ===
plugin config hello greeting=Hello
plugin reload hello
echo === 11. 未知插件 ===
plugin info 不存在的插件
echo === 12. plugin help ===
plugin help
echo === done ===
