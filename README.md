# GameKey Hub
模拟游戏cdkey交易平台，实现cdkey的购买、出售，同时能够查询史低价格并且给出购买建议(●'◡'●)
（当然里面的cdkey都是假的）

![【哲风壁纸】卡通-海绵宝宝-清新](https://github.com/user-attachments/assets/76b5d6bd-f8b1-4e9a-856b-c0ff39d54011)


## 实现的功能

买家：
1.浏览游戏库，查看当前最低价与“史低价”对比建议。
2.充值钱包余额。
3.购买 CDKey（要求系统保证并发安全，防止超卖）。
4.查看历史订单。

卖家：
1.发布闲置 CDKey，设定售价。
2.系统需自动根据新发布的价格更新游戏的“历史最低价”。

<img width="1965" height="1167" alt="image" src="https://github.com/user-attachments/assets/5291e9ee-0709-46d2-a0ba-17d49be4cece" />

<img width="1965" height="388" alt="image" src="https://github.com/user-attachments/assets/78eaf6d7-9381-47cb-b6cc-12b4b3512726" />

<img width="1745" height="503" alt="image" src="https://github.com/user-attachments/assets/1e5c276e-7e99-4983-8494-d34bfbdbfeda" />

<img width="1116" height="693" alt="image" src="https://github.com/user-attachments/assets/8378bed6-d2c1-4037-a97b-c6dc2984593b" />

<img width="1945" height="713" alt="image" src="https://github.com/user-attachments/assets/75207554-1e79-4ec8-b661-3ce4620d305b" />



## 数据流分析
用户发起购买请求 -> 后端开启数据库事务 -> 检查商品库存状态 -> 检查用户余额 -> 执行扣款与库存扣减 -> 提交事务 -> 生成订单记录

## 特点（可能？）
由于作者本人经常在游戏大促期间浏览交易平台时被卡得非常难受，于是想用借助这次大作业看看能不能解决“大促”场景下的并发冲突

1. 事务控制与防超卖
   系统采用了 **乐观锁** 结合 MySQL 事务机制。在购买环节，通过 Python 逻辑检查余额，利用 SQL 语句 `UPDATE ... WHERE status='available' LIMIT 1` 的原子性来确保同一时刻只有一个用户能买到同一个 Key，有效解决了“大促”场景下的并发冲突。
2. 购买建议算法
   后端实时读取 `current_price` (当前在售最低价) 与 `historical_low` (数据库触发器维护的史低价)。若 $Current \le Historical \times 1.05$，标记为“史低！买爆！”。此功能体现了应用层代码与数据库存储过程的协同工作。

## 实验总结
本次实验完成了一个功能完备的数据库应用系统。重点解决了以下问题：

1.数据完整性：通过外键约束和触发器，保证了商品与游戏、价格与史低记录的一致性。

2.事务处理：深入理解了 COMMIT 和 ROLLBACK 在电商交易中的决定性作用，确保了“钱货两清”。

3.工程化实践：完成了从数据库建表到 Web 前端展示的全栈开发流程 。

# 使用教程
下载整个仓库的文件，先用navicat运行一下`db_init.sql`文件，然后用`pycharm`运行app.py文件，点击终端里输出的网址就行了（没钱租服务器捏ㄒoㄒ）

<img width="566" height="82" alt="image" src="https://github.com/user-attachments/assets/4661329b-5f3a-48e9-8bda-384ed3468a96" />


管理员账户：admin
密码：123456
直接登录即可
