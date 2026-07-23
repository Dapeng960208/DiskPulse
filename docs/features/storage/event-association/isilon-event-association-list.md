# Dell PowerScale（Isilon） 事件关联信息清单

本清单由 `backend/scripts/initialize_vendor_event_definitions.py` 中的初始化目录生成，共 `531` 条；所有内置定义初始化时均为启用状态。

关联类型和审核边界见[厂商事件关联目录](overview.md)，待审核项的补证要求见[待核验厂商事件清单](unverified-code-list.md)。

| 事件代码 | 关联类型 | 中文标题 | 审核状态 | 适用版本 | 官网依据 |
| --- | --- | --- | --- | --- | --- |
| `100010001` | `capacity_threshold` | 节点上的 /var 分区已达到或接近容量。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010002` | `capacity_threshold` | 节点上的 /var/crash 分区已达到或接近容量。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010003` | `capacity_threshold` | 群集中一个或多个节点上的根文件系统已接近容量上限。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010004` | `capacity_threshold` | 群集上的 /ifs 分区已接近容量。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010005` | `fault_log` | 串行连接 SCSI (SAS) PHY 监视器检测到磁盘子系统中存在错误或更改。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010006` | `fault_log` | 驱动器记录了磁盘子系统中的错误或更改。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010007` | `fault_log` | 串行连接 SCSI (SAS) PHY 监视器检测到 SAS 电缆流量中误码率过高。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010008` | `fault_log` | 串行连接 SCSI (SAS) PHY 监视器检测到误码率过高并且 SAS 电缆上的流量被禁用。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010009` | `system_activity` | 磁盘修复已启动。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010010` | `system_activity` | 磁盘修复完成。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010011` | `fault_log` | 该节点中的一个或多个出现故障的驱动器已准备好进行更换。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010012` | `system_activity` | 磁盘已停止运行，正在评估磁盘运行状况。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010013` | `system_activity` | 磁盘扇区有错误。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010014` | `fault_log` | 磁盘 ECC 列表已满。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010015` | `capacity_threshold` | 群集上的磁盘池之一接近或已达到最大容量。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010016` | `fault_log` | 磁盘池元数据已写入的 SSD 数量多于布局首选项中分配的数量。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010017` | `fault_log` | 驱动器与节点配置信息不匹配。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010018` | `capacity_threshold` | 集群中 SSD 的存储容量已接近容量。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010019` | `telemetry_degradation` | 串行连接 SCSI (SAS) 控制器记录了磁盘子系统中的错误或更改。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010020` | `telemetry_degradation` | 串行连接 SCSI (SAS) 控制器记录了磁盘子系统中的错误或更改。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010021` | `telemetry_degradation` | 串行连接 SCSI (SAS) 链路已超过最大误码率 (BER)。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010022` | `telemetry_degradation` | 串行连接 SCSI (SAS) 链路因超出最大误码率 (BER) 而被禁用。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010023` | `fault_log` | 驱动器托架错误计数器已超过配置的阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010024` | `fault_log` | 所识别的驱动器型号缺少配置文件。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010025` | `fault_log` | 已超过已识别托架的 SMART 状态阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010026` | `fault_log` | 加密驱动器处于不安全状态 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010027` | `fault_log` | 驱动器子系统确定驱动器上的驱动器固件版本不正确。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010028` | `fault_log` | 驱动器子系统无法识别驱动器的驱动器固件版本。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010029` | `fault_log` | 驱动器子系统无法识别驱动器的型号。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010030` | `fault_log` | 节点中安装了不受支持的驱动器。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010031` | `fault_log` | 从节点删除加密驱动器时，该驱动器并未被擦除。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010032` | `fault_log` | 插入来自另一个集群的用过的驱动器作为替换。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010033` | `fault_log` | 插入集群中另一个节点的用过的驱动器作为替换。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010034` | `system_activity` | 驱动器的 FlexProtect 作业正在进行中。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010035` | `fault_log` | 插入先前出现故障的驱动器作为替换。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010036` | `system_activity` | 驱动器的磁盘修复过程已完成。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010037` | `fault_log` | 新驱动器未正确格式化，因此该驱动器未添加到文件系统中。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010038` | `fault_log` | 以下驱动器插入到包含另一个正在进行 smartfailing 的驱动器的托架中。重新插入发生 smartfailing 的驱动器，或等待 FlexProtect 作业完成后再插入新驱动器。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010039` | `fault_log` | 不可配置的驱动器：{不可配置} | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010041` | `fault_log` | 已尝试使用不受支持的启动闪存驱动器。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010042` | `fault_log` | SmartPools 升级期间发生错误，因此升级未完成。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010043` | `fault_log` | 必须更换节点启动闪存驱动器。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010044` | `fault_log` | 必须更换节点启动闪存驱动器。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010045` | `fault_log` | 节点启动闪存驱动器正在接收过多写入。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010046` | `fault_log` | 节点池中有一个节点的 SSD 数量与池中其他节点的 SSD 数量不匹配。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010050` | `system_activity` | smartfail 过程在驱动器上完成。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010051` | `system_activity` | smartfail 过程在驱动器上完成。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010052` | `fault_log` | 驱动器不再作为集群的一部分出现，并且正在发生 smartfailed。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010053` | `fault_log` | 第 6 代平台中安装了启用写入缓存的驱动器。支持写入缓存的驱动器与第 6 代节点不兼容。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010054` | `fault_log` | 驱动器插入到已禁用的托架中。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010055` | `fault_log` | 第 6 代平台中安装了启用写入缓存的驱动器。启用写入缓存的驱动器与第 6 代节点不兼容，并且驱动器已发生 smartfailed。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010056` | `fault_log` | 第 6 代平台中的驱动器启用了写入缓存。支持写入缓存的驱动器与第 6 代节点不兼容。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010057` | `fault_log` | Gen6 上缺少一张 m.2 卡。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010058` | `capacity_threshold` | 节点池不满足大文件的最小存储空间要求：{node_pool_name} (id={node_pool_id}) | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010059` | `capacity_threshold` | 节点池 {nodepool_name}（节点池 ID：{nodepool_id}）已达到或超过大文件的容量。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010060` | `fault_log` | PCI 驱动器中检测到错误：位置 {location}，类型 {media_type}，LNUM {disk}：{aer}。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010061` | `fault_log` | 在 NVMe 驱动器中检测到错误：位置 {location}，类型 {media_type}，LNUM {disk}：{detail}。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100010062` | `fault_log` | NVMe 驱动器连接检测到 PCI 链路错误。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100020060` | `fault_log` | 驱动器底座已从机箱中移除，并且底座服务超时限制已过期。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100020061` | `fault_log` | 驱动器滑板意外地从底盘上拆下。雪橇上的所有驱动器均已暂停。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100020062` | `fault_log` | 在驱动滑板中检测到故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100020063` | `fault_log` | 驱动器底座从机箱中移除的时间超过了超时限制。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `100030001` | `fault_log` | 驱动器已被标记为正在耗尽，但使用率很低。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `1100000001` | `fault_log` | CloudPools 网络连接失败。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `1100000002` | `fault_log` | CloudPools 用户无法进行身份验证。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `1100000003` | `fault_log` | 云帐户尝试访问它没有权限的文件。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `1100000004` | `fault_log` | 未找到 Amazon S3 遥测报告存储桶。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `1100000005` | `capacity_threshold` | 超出了 Cloudpool 容量阈值。说明 默认情况下，当云提供商的数据量达到 70% 时，首先出现此事件。当超出以下容量阈值时，该事件将通知您： 70% 信息性 80% 警告 90% 严重 95% 紧急 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `1100000006` | `fault_log` | CloudPools 数据已损坏。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `1100000007` | `fault_log` | CloudPools 未找到可用帐户。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `1100000008` | `fault_log` | CloudPools 无法验证提供商证书。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `200010001` | `fault_log` | 集群中的一个或多个节点脱机或无法访问。由于以下情况之一，一个或多个节点离线： ● 节点被故意关闭以进行维护。 ● 节点缺乏内部网络连接。内部连接是节点与集群上其他节点通信的方式。 ● 节点不能加入组。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `200010002` | `system_activity` | 之前离线的节点已重新加入组。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `200010003` | `fault_log` | 一个或多个节点离线。由于以下情况之一，一个或多个节点离线： ● 节点被故意关闭以进行维护。 ● 节点缺乏内部网络连接。内部连接是节点与集群上其他节点通信的方式。 ● 节点不能加入组。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `200010006` | `fault_log` | 所识别的节点组未受到足够的数据丢失保护。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `200010007` | `fault_log` | 未配置所识别的节点。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `200010008` | `fault_log` | 已识别的节点池配置不足。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `200010009` | `fault_log` | Node 已经从恐慌中恢复过来。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `200020001` | `fault_log` | 以太网链路未以最大吞吐量运行。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `200020002` | `fault_log` | 一个或多个节点上的 10 GigE 接口遇到了网络连接问题。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `200020003` | `fault_log` | 检测到多个内部网络问题。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `200020004` | `fault_log` | 一个或多个节点在其聚合网络接口上遇到了网络连接问题。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `200020005` | `fault_log` | 集群中的一个节点在其一个或两个外部接口上失去了网络连接。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `200020006` | `fault_log` | 所识别的 InfiniBand 接口的链路状态快速且反复变化。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `200020007` | `fault_log` | 内部网络交换机和 SNMP 服务器不通信。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `200020008` | `fault_log` | 内部网络交换机中的风扇发生故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `200020009` | `fault_log` | 内部网络交换机的电源出现故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `200020010` | `fault_log` | 内部网络交换机发生故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `200020011` | `fault_log` | 40 Gb 以太网链路未以最大吞吐量运行。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `200020012` | `fault_log` | 管理以太网链路未以最大吞吐量运行。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `200020013` | `fault_log` | 内部网络以太网链路未以最大吞吐量运行。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `200020014` | `capacity_threshold` | 10 吉比特以太网链路 {ifname} 在低于容量的情况下运行。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `200020015` | `capacity_threshold` | 100 吉比特以太网链路 {ifname} 在低于容量的情况下运行。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `200020020` | `fault_log` | 群集中的节点之一已失去外部网络连接。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `200020021` | `fault_log` | 戴尔交换机存在布线问题。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `200020022` | `fault_log` | 后端结构无法联系后端 Dell 主交换机。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `200020023` | `fault_log` | 叶交换机和主干交换机的带宽不同。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `200020024` | `performance_anomaly` | 结构带宽不一致。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `200020025` | `fault_log` | 后端网络无连接。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `200020026` | `fault_log` | 网络接口卡不健康。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `200030001` | `fault_log` | 集群没有最新的固件。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `200030002` | `fault_log` | 集群没有可用的固件包。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `300010001` | `performance_anomaly` | 出于维护目的，该节点正在重新启动。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `300010002` | `performance_anomaly` | 出于维护目的，该节点正在关闭。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `300010003` | `fault_log` | 节点在指定时间内重启失败。由于以下情况之一，一个或多个节点离线： ● 节点被故意关闭以进行维护。 ● 节点缺乏内部网络连接。内部连接是节点与集群上其他节点通信的方式。 ● 节点不能加入组。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `300020001` | `fault_log` | 节点上的只读转换失败。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `300020002` | `system_activity` | 节点日志备份验证失败。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `300020003` | `fault_log` | 节点在执行最终关闭时遇到错误。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400020001` | `performance_anomaly` | 由于当前内存阈值设置，LWIO 正在受到限制。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400030001` | `fault_log` | 尽管多次尝试启动进程，但仍无法重新启动该进程。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400030002` | `system_activity` | 主控制程序 (MCP) 停止了一个进程。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400040001` | `fault_log` | 检测到 SyncIQ 策略问题。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400040002` | `fault_log` | SyncIQ 策略失败。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400040003` | `fault_log` | SyncIQ 策略无法启动。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400040004` | `capacity_threshold` | SyncIQ 作业的目标集群无法创建请求的快照。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400040005` | `unknown` | SRS Brevity 事件 400040005 | `pending` | — | [官方文档](<https://infohub.delltechnologies.com/en-us/l/powerscale-onefs-advanced-alert-configurations/appendix-b-full-list-of-srs-brevity/>) |
| `400040007` | `fault_log` | 目标集群上的文件已被修改。 SyncIQ 正在覆盖那些已修改的文件。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400040008` | `unknown` | SRS Brevity 事件 400040008 | `pending` | — | [官方文档](<https://infohub.delltechnologies.com/en-us/l/powerscale-onefs-advanced-alert-configurations/appendix-b-full-list-of-srs-brevity/>) |
| `400040009` | `fault_log` | SyncIQ 计划程序无法启动计划的策略。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400040010` | `fault_log` | 发生 SyncIQ 策略配置错误。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400040011` | `fault_log` | SyncIQ 正在尝试同步到不兼容的目标版本。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400040012` | `fault_log` | 发生 SyncIQ 配置错误。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400040014` | `fault_log` | SyncIQ 无法联系目标集群。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400040015` | `fault_log` | SyncIQ 无法拍摄策略快照。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400040016` | `unknown` | SRS Brevity 事件 400040016 | `pending` | — | [官方文档](<https://infohub.delltechnologies.com/en-us/l/powerscale-onefs-advanced-alert-configurations/appendix-b-full-list-of-srs-brevity/>) |
| `400040017` | `fault_log` | SyncIQ 文件系统上的策略存在错误。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400040018` | `fault_log` | SyncIQ 策略升级失败。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400040019` | `fault_log` | SyncIQ 在连接到 SyncIQ 策略中配置的目标集群时遇到问题。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400040020` | `performance_anomaly` | SyncIQ 策略超出了恢复点目标 (RPO)。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400040021` | `fault_log` | SyncIQ SnapRevert 作业解决了 WORM 提交的文件之间的冲突。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400040022` | `fault_log` | SyncIQ 策略无法与目标建立加密连接。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400040023` | `fault_log` | SyncIQ 在服务导出期间遇到错误。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400040024` | `fault_log` | SyncIQ 策略检测到目标上不支持的 WORM 设置。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400040025` | `fault_log` | SyncIQ 策略正在等待 Cloudpools 准备存根 LIN。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400040026` | `fault_log` | SyncIQ 源集群和目标集群之间的最大文件名长度支持有所不同。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400050001` | `system_activity` | 此事件是作为测试生成的。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400050002` | `system_activity` | 此事件是作为测试生成的。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400050003` | `system_activity` | 集群已上报消息。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400050004` | `system_activity` | 这是一个心跳事件，确认事件系统是健康的。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400060001` | `fault_log` | AVScan 服务已启用，但尚未输入防病毒 ICAP 服务器的 URL。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400060002` | `fault_log` | 群集无法访问任何防病毒 ICAP 服务器或 ICAP 服务器无响应。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400060004` | `fault_log` | 病毒扫描软件已识别出受病毒感染的文件。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400060101` | `fault_log` | 未配置 CEE/CAVA 服务器。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400060102` | `fault_log` | 所有 CEE/CAVA 防病毒服务器均已禁用。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400060103` | `fault_log` | 对于集群大小而言，CEE/CAVA 服务器不足。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400060104` | `fault_log` | 所有 CEE/CAVA 服务器均处于离线状态。节点上的所有防病毒服务器当前均报告为脱机。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400060105` | `fault_log` | CEE/CAVA服务器上的防病毒软件出现错误或运行不正常。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400060106` | `fault_log` | CEE/CAVA 服务器离线。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400060107` | `fault_log` | 所有访问区域都禁用了 CEE 或 CAVA 防病毒功能。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400060108` | `fault_log` | 防病毒服务发现受感染的文件。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400060109` | `fault_log` | 防病毒访问区域丢失。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400060110` | `fault_log` | 防病毒 IP 池丢失或配置错误。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400060111` | `fault_log` | Windows 服务器上安装的 CAVA 代理版本错误。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400060112` | `fault_log` | 节点上所需的 SMB 服务不可用。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400060113` | `fault_log` | CAVA 筛选器驱动程序离线。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400070004` | `fault_log` | OneFS 软件模块的评估许可证预计即将到期。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400070005` | `fault_log` | OneFS 软件模块的评估许可证已过期。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400070006` | `system_activity` | 许可证的激活未完成。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400070007` | `capacity_threshold` | 集群正在使用未经许可的软件。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400080001` | `fault_log` | 固件升级失败：{msg} | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400090001` | `system_activity` | 该事件每月生成一次，以提供一般集群信息。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400090002` | `fault_log` | 该集群包含加密节点和非加密节点的混合。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400090003` | `fault_log` | 未配置安全远程支持 (SRS)。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400090004` | `fault_log` | 群集与安全远程支持 (SRS) 网关服务器失去连接。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400100001` | `system_activity` | 工作状态发生了变化。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400100002` | `system_activity` | 作业引擎阶段开始。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400100003` | `system_activity` | 一个工作阶段结束了。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400100004` | `system_activity` | 工作失败了。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400100005` | `system_activity` | 发生了就业政策事件。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400100006` | `fault_log` | 作业 {job_type} 未能按计划启动。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400100007` | `fault_log` | 发生作业引擎事件。集群已满，无法再写入数据。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400100008` | `fault_log` | 发生作业引擎事件。文件写入操作停止，或者写入集群的速度非常慢。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400100009` | `system_activity` | 一个或多个节点已被排除在参与此作业之外。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400100010` | `fault_log` | 一个或多个不存在的节点已被排除在参与此作业之外。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400100011` | `fault_log` | 集群必须重新条带化，但 FlexProtect 未运行。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400110001` | `fault_log` | 系统内存不足，指定的进程已停止以释放内存。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400120001` | `fault_log` | 其中一个启动磁盘运行状况不佳，启动数据不再在两个启动磁盘之间进行镜像。剩余启动盘丢失将导致节点故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400130001` | `fault_log` | NFS 导出规则的配置方式使得客户端无法挂载路径。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400130002` | `fault_log` | 处理 NFS 导出规则时，尝试查找指定主机的 DNS 名称失败。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400140001` | `fault_log` | NFSv4 服务器无法查找用户或组名以映射到用户 ID (UID) 或组 ID (GID)。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400140002` | `fault_log` | NFS 无法将 64 位 cookie 转换为 32 位 cookie。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400140003` | `fault_log` | 要使用 NFSv3-over-RDMA 功能，集群必须具有支持 RDMA 的前端网络接口卡。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400150001` | `system_activity` | OneFS 升级开始。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400150002` | `system_activity` | OneFS 升级成功完成。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400150003` | `fault_log` | OneFS 升级正在进行中。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400150004` | `fault_log` | OneFS 升级过程中的某个步骤所花费的时间比预期要长。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400150005` | `system_activity` | OneFS 升级回滚已开始。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400150006` | `fault_log` | 代理未准备好。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400150007` | `fault_log` | 升级挂起 - 无法与设备上的升级代理通信：{devids} | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400150008` | `fault_log` | 挂钩/命令运行时间太长。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400150009` | `capacity_threshold` | 并行升级在 PendingReboot 挂钩处停止。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400150010` | `fault_log` | 升级在节点上停滞 - 无法在不冒数据不可用 (DU) 风险的情况下启动重新启动。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400150011` | `fault_log` | 升级耗尽警报 - 无法在没有潜在客户端中断的情况下重新启动节点 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400160001` | `fault_log` | 群集无法访问外部 Common Event Enabler (CEE) 服务器，或者 CEE 服务器无响应。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400170001` | `fault_log` | 定期检查商店是否发现过期证书。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400170002` | `fault_log` | 定期检查商店是否发现过期的证书。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400180001` | `fault_log` | 节点 {lnn} 上的内联重复数据删除分配失败，发生次数 {occurrence} | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400180002` | `fault_log` | 节点 {lnn} 上正在进行内联重复数据删除分配，发生次数 {occurrence} | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400180003` | `fault_log` | 节点 {lnn} 上不支持内联重复数据删除分配，发生次数 {occurrence} | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400180004` | `performance_anomaly` | 节点 {lnn} 上的索引较小，出现 {occurrence} 时，内联重复数据删除运行性能下降。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400180005` | `fault_log` | 内联重复数据删除索引在节点 {lnn} 上具有非标准布局，出现次数 {occurrence} | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400190001` | `fault_log` | 重复数据删除目录 {path} 无效 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400200001` | `unknown` | 未收录的厂商事件代码 | `pending` | — | — |
| `400200002` | `unknown` | 未收录的厂商事件代码 | `pending` | — | — |
| `400210001` | `fault_log` | 自加密驱动器 (SED) 的加密密钥管理器无法在指示的节点上启动。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400210002` | `fault_log` | Cloudpools 的加密密钥管理器无法在指示的节点上启动。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400210003` | `fault_log` | 密钥管理器控制密钥在硬件中不可用。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400210004` | `fault_log` | KMIP 服务器返回错误。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400210005` | `fault_log` | 到达 KMIP 服务器时发生网络错误。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400210006` | `fault_log` | KMIP 密钥迁移失败。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400210007` | `fault_log` | KMIP 服务器的证书即将过期。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400210008` | `fault_log` | KMIP 服务器的证书已过期。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400220000` | `system_activity` | PDM 降级，操作过多 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400230001` | `fault_log` | 用户对 SSHD 所做的无效配置更改。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400240000` | `fault_log` | S3 服务启动失败。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400240001` | `fault_log` | 身份查询失败 user=1000 名称 status=STATUS_ACCESS_DENIED。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400240002` | `fault_log` | S3 名称查询失败 user=alice 到 id status=STATUS_ACCESS_DENIED。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400240003` | `fault_log` | S3 无法解析存储桶 ID 的 MPU 信息：123456。上传 ID 987654。SBT 可能已损坏。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400240004` | `fault_log` | SBT 中的 S3 密钥无效。 SBT 可能会被破坏。当前基本密钥 = a/b/c。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400240005` | `fault_log` | SBT 中的 S3 密钥已满。存储桶的 SBT 可能已满 - 123456。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400250000` | `fault_log` | 发现并忽略了不兼容的用户指定的补丁。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `400260000` | `unknown` | 未收录的厂商事件代码 | `pending` | — | — |
| `500010001` | `capacity_threshold` | SmartQuotas 模块已通知用户配额违规。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `500010002` | `capacity_threshold` | SmartQuotas 通知功能失败。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `500010003` | `capacity_threshold` | SmartQuotas 配置文件已损坏或无效。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `500010004` | `capacity_threshold` | SmartQuotas 配置文件已损坏或无效。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `500010005` | `capacity_threshold` | SmartQuotas 模块无法生成请求的配额报告。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `600010001` | `fault_log` | 快照守护程序无法创建计划的快照。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `600010002` | `fault_log` | 快照守护程序无法删除过期的快照。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `600010003` | `fault_log` | 快照守护程序无法删除快照锁。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `600010004` | `fault_log` | snapshot_schedule.xml 文件已损坏或无法读取。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `600010005` | `fault_log` | 集群上存储的数据量接近或超过快照预留空间。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `700010001` | `fault_log` | 群集时间与 Windows Active Directory 服务器不同。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `700010003` | `fault_log` | 无法联系 Windows 时间服务器。集群时间不同步。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `700010004` | `fault_log` | 发生 SMB 升级错误，这可能会影响 SMB 服务的行为。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `700010005` | `fault_log` | 发生身份验证升级失败。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `700020001` | `fault_log` | Windows UID 映射范围已满。在范围扩大之前，身份验证可能会失败。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `700020002` | `fault_log` | Windows GID 映射范围已满。在范围扩大之前，身份验证可能会失败。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `700020003` | `fault_log` | Windows 网络服务无法解析 idmap 规则。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `700030001` | `fault_log` | 存储在群集上的 Active Directory 帐户数据已被删除或损坏。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `700030002` | `fault_log` | Active Directory 服务器脱机。身份验证服务可能会中断。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `700030003` | `fault_log` | 该节点无法对认证数据库文件进行读写操作。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `700030004` | `fault_log` | 鉴权服务不可用。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `700030005` | `fault_log` | Active Directory 服务提供商缺少所需的 SPN。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `700030006` | `fault_log` | Active Directory 计算机无效。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `700040001` | `fault_log` | LDAP 服务器离线。身份验证服务可能会中断。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `700050001` | `fault_log` | NIS 服务器离线。身份验证服务可能会中断。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `700100001` | `system_activity` | LWIO 参数无效。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `800010002` | `fault_log` | 系统检测到元数据引用完整性错误，需要手动干预才能解决。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `800010003` | `fault_log` | 检测到 Isilon 数据完整性 (IDI) 故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `800010004` | `fault_log` | 集群遇到文件系统错误。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `800010005` | `fault_log` | 动态扇区修复 (DSR) 过程无法解决数据验证错误。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `800010006` | `fault_log` | 节点报告可用文件描述符的数量已接近最大限制。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `800010007` | `fault_log` | 检测到 Isilon 数据完整性 (IDI) 网络校验和错误。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `800010008` | `system_activity` | NVRAM 日志大于日志备份分区。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `800010009` | `system_activity` | 计算 NVRAM 日志备份的分区大小时出错。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `800010010` | `fault_log` | 节点无法验证其对等节点上日志的备份副本。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900010000` | `unknown` | SRS Brevity 事件 900010000 | `pending` | — | [官方文档](<https://infohub.delltechnologies.com/en-us/l/powerscale-onefs-advanced-alert-configurations/appendix-b-full-list-of-srs-brevity/>) |
| `900010001` | `fault_log` | 节点主板上存在错误，例如时钟电池故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900010002` | `fault_log` | 该节点需要更换电池。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900010003` | `fault_log` | NVRAM 卡有问题。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900010004` | `fault_log` | 传感器检测到节点机箱打开。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900010005` | `fault_log` | 节点中发生内存、PCI 或 PCIe 总线错误。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900010006` | `fault_log` | 节点中发生内存、PCI 或 PCIe 总线错误。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900010007` | `fault_log` | <DIMM> 超出了可纠正内存错误率。尽快更换 DIMM。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900010008` | `fault_log` | 检测到 I2C 总线存在硬件问题。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900010009` | `fault_log` | 节点的驱动比错误。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900010010` | `fault_log` | 该节点具有 812（3/4 机箱）SKU。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900010011` | `fault_log` | 底板管理控制器 (BMC) 或机箱管理控制器 (CMC) 无响应。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900010012` | `fault_log` | 节点中的保险丝可能发生故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900010013` | `fault_log` | 指定设备的固件更新失败。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900020001` | `fault_log` | 节点前面板上的传感器已超过指定阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900020002` | `fault_log` | 节点中的电源风扇可能出现故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900020003` | `fault_log` | 节点中的电源风扇可能出现故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900020004` | `fault_log` | 节点中的电源风扇可能出现故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900020005` | `fault_log` | 节点中的电源风扇可能出现故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900020006` | `fault_log` | 节点中的机箱风扇可能发生故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900020007` | `fault_log` | 节点中的机箱风扇可能发生故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900020008` | `fault_log` | 节点中的机箱风扇可能发生故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900020009` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900020010` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900020011` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900020012` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900020013` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900020014` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900020015` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900020016` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900020017` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900020018` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900020019` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900020020` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900020021` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900020022` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900020023` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900020024` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900020025` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900020026` | `fault_log` | 节点周围的内部或环境温度超过了CPU允许的阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900020027` | `fault_log` | 节点周围的内部或环境温度超过了CPU允许的阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900020028` | `fault_log` | 节点周围的内部或环境温度已超过电源允许的阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900020029` | `fault_log` | 节点周围的内部或环境温度已超过电源允许的阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900020030` | `fault_log` | 节点周围的内部或环境温度超过允许阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900020031` | `fault_log` | 节点前面板内部或环境温度超过允许阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900020032` | `fault_log` | 节点周围的内部或环境温度已超过机箱允许的阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900020033` | `fault_log` | 节点中的一个电源发生故障或断电。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900020034` | `fault_log` | 节点报告的物理内存量低于预期。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900020035` | `fault_log` | 节点周围的内部或环境温度超过了CPU允许的阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900030023` | `unknown` | SRS Brevity 事件 900030023 | `pending` | — | [官方文档](<https://infohub.delltechnologies.com/en-us/l/powerscale-onefs-advanced-alert-configurations/appendix-b-full-list-of-srs-brevity/>) |
| `900040035` | `unknown` | SRS Brevity 事件 900040035 | `pending` | — | [官方文档](<https://infohub.delltechnologies.com/en-us/l/powerscale-onefs-advanced-alert-configurations/appendix-b-full-list-of-srs-brevity/>) |
| `900060001` | `fault_log` | 节点前面板上的传感器已超过指定阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060002` | `fault_log` | 节点中的电源风扇可能出现故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060003` | `fault_log` | 节点中的电源风扇可能出现故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060004` | `fault_log` | 节点中的机箱风扇可能发生故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060005` | `fault_log` | 节点中的机箱风扇可能发生故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060006` | `fault_log` | 节点中的机箱风扇可能发生故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060007` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060008` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060009` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060010` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060011` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060012` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060013` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060014` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060015` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060016` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060017` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060018` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060019` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060020` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060021` | `fault_log` | 节点周围的内部或环境温度超过了CPU允许的阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060022` | `fault_log` | 节点周围的内部或环境温度超过了CPU允许的阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060023` | `fault_log` | 节点周围的内部或环境温度超过允许阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060024` | `fault_log` | 节点前面板内部或环境温度超过允许阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060025` | `fault_log` | 节点周围的内部或环境温度已超过机箱允许的阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060026` | `fault_log` | 节点周围的内部或环境温度超过了CPU允许的阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060027` | `fault_log` | 节点中的一个电源发生故障或断电。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060028` | `fault_log` | 节点报告的物理内存量低于预期。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060029` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060030` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060031` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060032` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060033` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060034` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060035` | `fault_log` | 节点中的电源风扇可能出现故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060036` | `fault_log` | 节点中的电源风扇可能出现故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060037` | `fault_log` | 节点中的一个电源发生故障或断电。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060038` | `fault_log` | 节点中的一个电源发生故障或断电。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060039` | `fault_log` | 节点周围的内部或环境温度已超过电源允许的阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900060040` | `fault_log` | 节点周围的内部或环境温度已超过电源允许的阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080001` | `fault_log` | 节点前面板上的传感器已超过指定阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080002` | `fault_log` | 节点中的电源风扇可能出现故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080003` | `fault_log` | 节点中的电源风扇可能出现故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080004` | `fault_log` | 节点中的电源风扇可能出现故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080005` | `fault_log` | 节点中的电源风扇可能出现故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080006` | `fault_log` | 节点中的机箱风扇可能发生故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080007` | `fault_log` | 节点中的机箱风扇可能发生故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080008` | `fault_log` | 节点中的机箱风扇可能发生故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080009` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080010` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080011` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080012` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080013` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080014` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080015` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080016` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080017` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080018` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080019` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080020` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080021` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080022` | `fault_log` | 节点中的一个电源发生故障或断电。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080023` | `fault_log` | 节点中的一个电源发生故障或断电。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080024` | `fault_log` | 节点中的一个电源发生故障或断电。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080025` | `fault_log` | 节点中的一个电源发生故障或断电。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080026` | `fault_log` | 节点周围的内部或环境温度超过了CPU允许的阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080027` | `fault_log` | 节点周围的内部或环境温度超过了CPU允许的阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080028` | `fault_log` | 节点周围的内部或环境温度已超过电源允许的阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080029` | `fault_log` | 节点周围的内部或环境温度已超过电源允许的阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080030` | `fault_log` | 节点周围的内部或环境温度超过允许阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080031` | `fault_log` | 节点前面板内部或环境温度超过允许阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080032` | `fault_log` | 节点周围的内部或环境温度已超过机箱允许的阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080033` | `fault_log` | 节点中的一个电源发生故障或断电。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080034` | `fault_log` | 节点报告的物理内存量低于预期。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080035` | `fault_log` | 节点周围的内部或环境温度超过了CPU允许的阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080036` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900080037` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900090025` | `unknown` | SRS Brevity 事件 900090025 | `pending` | — | [官方文档](<https://infohub.delltechnologies.com/en-us/l/powerscale-onefs-advanced-alert-configurations/appendix-b-full-list-of-srs-brevity/>) |
| `900100001` | `fault_log` | 指示节点中的 NVRAM 遇到单位错误。 ECC 自动更正错误。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900100004` | `fault_log` | PCIe 通道宽度未成功协商。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900100010` | `unknown` | SRS Brevity 事件 900100010 | `pending` | — | [官方文档](<https://infohub.delltechnologies.com/en-us/l/powerscale-onefs-advanced-alert-configurations/appendix-b-full-list-of-srs-brevity/>) |
| `900100011` | `unknown` | SRS Brevity 事件 900100011 | `pending` | — | [官方文档](<https://infohub.delltechnologies.com/en-us/l/powerscale-onefs-advanced-alert-configurations/appendix-b-full-list-of-srs-brevity/>) |
| `900100012` | `unknown` | SRS Brevity 事件 900100012 | `pending` | — | [官方文档](<https://infohub.delltechnologies.com/en-us/l/powerscale-onefs-advanced-alert-configurations/appendix-b-full-list-of-srs-brevity/>) |
| `900100013` | `unknown` | SRS Brevity 事件 900100013 | `pending` | — | [官方文档](<https://infohub.delltechnologies.com/en-us/l/powerscale-onefs-advanced-alert-configurations/appendix-b-full-list-of-srs-brevity/>) |
| `900100014` | `unknown` | SRS Brevity 事件 900100014 | `pending` | — | [官方文档](<https://infohub.delltechnologies.com/en-us/l/powerscale-onefs-advanced-alert-configurations/appendix-b-full-list-of-srs-brevity/>) |
| `900100015` | `unknown` | SRS Brevity 事件 900100015 | `pending` | — | [官方文档](<https://infohub.delltechnologies.com/en-us/l/powerscale-onefs-advanced-alert-configurations/appendix-b-full-list-of-srs-brevity/>) |
| `900100016` | `unknown` | SRS Brevity 事件 900100016 | `pending` | — | [官方文档](<https://infohub.delltechnologies.com/en-us/l/powerscale-onefs-advanced-alert-configurations/appendix-b-full-list-of-srs-brevity/>) |
| `900100017` | `unknown` | SRS Brevity 事件 900100017 | `pending` | — | [官方文档](<https://infohub.delltechnologies.com/en-us/l/powerscale-onefs-advanced-alert-configurations/appendix-b-full-list-of-srs-brevity/>) |
| `900100018` | `fault_log` | NVRAM 板无法响应识别控制器命令。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900100019` | `fault_log` | 消息已从 NVRAM 卡发送到主机节点。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900100020` | `fault_log` | NVRAM 卡没有响应，节点已设置为只读。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900100021` | `fault_log` | NVRAM 卡未响应 armVault 命令，并且节点已设置为只读。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900100022` | `fault_log` | NVRAM 卡未响应 NVRAM 命令，且节点已设置为只读。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900100023` | `fault_log` | NVRAM 卡固件报告了可纠正的错误。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900100024` | `fault_log` | NVRAM 卡固件报告了无法纠正的错误。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900100025` | `fault_log` | 指示节点中的 NVRAM 闪存保管库无法在节点启动时正确解除武装。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900100026` | `performance_anomaly` | NVRAM 卡未获取必要的 msi-x 资源。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900100027` | `fault_log` | PCI 通道速度未成功协商。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900100028` | `fault_log` | NVDIMM 已失去机箱 ({chassis}) 中的持久性。为了保护日志，将节点设置为只读。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900100029` | `system_activity` | NVDIMM 已恢复在机箱 ({chassis}) 中的持久性。节点将重新启动以重新配置 NVDIMM。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900100030` | `fault_log` | 机箱 ({chassis}) 中 DIMM 插槽中的 NVDIMM 出现故障。在更换 NVDIMM 之前，将节点设置为只读 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900100031` | `fault_log` | 机箱 ({chassis}) 中的 NVDIMM 位于错误的 DIMM 插槽中。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900100032` | `telemetry_degradation` | 机箱 ({chassis}) 中未监控 NVDIMM 子系统运行状况。在问题解决之前，将节点设置为只读 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900110001` | `fault_log` | 节点周围的内部或环境温度超过了CPU允许的阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900110002` | `fault_log` | 节点前面板上的传感器已超过指定阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900110003` | `fault_log` | 节点报告的物理内存量低于预期。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900110004` | `fault_log` | 节点中的一个电源发生故障或断电。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900110005` | `fault_log` | 节点中的一个电源发生故障或断电。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900120001` | `fault_log` | 节点周围的内部或环境温度超过了CPU允许的阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900120002` | `fault_log` | 节点前面板上的传感器已超过指定阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900120003` | `fault_log` | 节点报告的物理内存量低于预期。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900120004` | `fault_log` | 节点中的一个电源发生故障或断电。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900120005` | `fault_log` | 节点中的一个电源发生故障或断电。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900130001` | `fault_log` | 节点周围的内部或环境温度超过了CPU允许的阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900130002` | `fault_log` | 节点前面板上的传感器已超过指定阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900130003` | `fault_log` | 节点报告的物理内存量低于预期。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900130004` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900130005` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900130006` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900130007` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900130008` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900130009` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900130010` | `fault_log` | 电源风扇可能出现故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900130011` | `fault_log` | 电源风扇可能出现故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900130013` | `fault_log` | 节点周围的内部或环境温度已超过电源允许的阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900130014` | `fault_log` | 节点中的一个电源发生故障或断电。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900130015` | `fault_log` | 节点中的一个电源发生故障或断电。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900140001` | `fault_log` | 节点上报电压测量事件组。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900140002` | `fault_log` | 指示节点上的风扇传感器值超出正常范围。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900140003` | `fault_log` | 指示节点上的电压传感器值超出正常范围。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900140004` | `fault_log` | 节点周围的内部或环境温度超过允许阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900140005` | `fault_log` | 有多个电源问题可能导致此事件发生。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900150001` | `fault_log` | 节点报告的物理内存量低于预期。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900160001` | `fault_log` | 节点未连接到其对等节点。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900160002` | `fault_log` | 节点无法连接到其对等节点。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900160003` | `fault_log` | 计算节点发生故障，可能需要更换。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900160004` | `fault_log` | 检测到 DIMM 故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900160005` | `fault_log` | 节点因热问题而断电。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900160006` | `fault_log` | 检测到风扇故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900160007` | `fault_log` | 检测到电源故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900160008` | `fault_log` | 检测到电池备用单元故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900160009` | `fault_log` | 检测到内部 M.2 驱动器故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900160010` | `fault_log` | 检测到 IO 模块故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900160011` | `fault_log` | 检测到内部故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900160012` | `fault_log` | 检测到外部故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900160013` | `fault_log` | 检测到非透明桥故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900160014` | `fault_log` | 检测到 I2C 总线存在硬件问题。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900160015` | `fault_log` | 检测到驱动器接口板故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900160016` | `fault_log` | 检测到中板故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900160017` | `system_activity` | 节点通电后无法恢复日志。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900160018` | `fault_log` | 电源不再为系统供电。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900160019` | `fault_log` | 未启用断电时的日志保护。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900160020` | `fault_log` | 硬件错误已得到纠正。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900160021` | `fault_log` | 节点的底板管理控制器 (BMC) 没有响应。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900160022` | `fault_log` | 对等节点中的底板管理控制器 (BMC) 没有响应。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900160023` | `fault_log` | 节点日志处于不受保护状态。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900160024` | `fault_log` | 发生延迟重新启动事件，并且识别的节点被设置为只读以保护日志。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900160100` | `fault_log` | 指定节点中没有可用的网络接口卡 (NIC)。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900160101` | `fault_log` | 网络接口卡 (NIC) 未在指定节点中正常运行。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900160102` | `fault_log` | 指定节点中发生网络接口卡 (NIC) 重置。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900170001` | `fault_log` | DHCP 服务器分配给 BMC LAN 接口的 IP 地址与外部网络已使用的子网重叠。 BMC LAN IP 地址不会被跟踪和用于外部接口的验证。 { 消息} | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900170002` | `fault_log` | 系统需要以下最低固件级别才能支持远程 IPMI 管理。 SSP：最低版本：{版本}。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900180001` | `fault_log` | 无法与 iDRAC 管理服务通信：{协议}。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900180002` | `fault_log` | 无法与内部双 SD 模块 (IDSDM) 通信。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900180003` | `fault_log` | 节点 {Inn} 需要重新启动才能使 BIOS 更改生效。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900180004` | `fault_log` | 风扇发生故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900180005` | `fault_log` | NVDIMM 电池出现故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900180006` | `fault_log` | NVDIMM 电池电量低且低于可接受的阈值，并且保管库可能会出现故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900180007` | `fault_log` | 在超过时间阈值的情况下，NVDIMM 电池电量一直较低。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900180008` | `fault_log` | 节点上的 DIMM 发生故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900180009` | `fault_log` | 物理安全传感器检测到发生了入侵错误。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900180010` | `fault_log` | 物理安全传感器不健康并且需要维护。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900180011` | `fault_log` | 系统板传感器 {sensor_name} 检测到某个组件正在 {adj} 建议的温度范围内运行。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900180012` | `fault_log` | 机箱温度传感器“{sensor_name}”运行状况不佳，需要维护。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900180013` | `fault_log` | 电源不健康，可能需要维护。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900180014` | `fault_log` | 电源已失去冗余。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900180015` | `fault_log` | 系统{desc}传感器检测到可能需要维护的退化或不健康的组件。传感器：{sensor_list}。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900180016` | `fault_log` | 系统{desc}传感器不健康，可能需要维护。传感器：{sensor_list}。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900180028` | `fault_log` | NVDIMM 已失去持久性。将节点设置为只读以保护日志。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900180029` | `system_activity` | NVDIMM 又恢复了持久性。节点自行重新启动以重新配置 NVDIMM。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900180030` | `fault_log` | NVDIMM 发生故障。节点转换为只读模式，直到更换 NVDIMM。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900180031` | `fault_log` | NVDIMM 位于错误的 DIMM 插槽中。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `900180032` | `fault_log` | 未监控 NVDIMM 子系统运行状况。节点将转换为只读模式，直到问题得到解决。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `910100001` | `fault_log` | 节点中的风扇可能发生故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `910100002` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `910100003` | `fault_log` | 节点周围的内部或环境温度超过允许阈值。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `910100004` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `910100005` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `910100006` | `fault_log` | 电压分量不符合规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `910100007` | `fault_log` | 节点前面板的传感器超出指定阈值 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `920100000` | `fault_log` | 有多个温度问题可能导致此事件发生。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `920100001` | `fault_log` | 有多个电池问题可能导致此事件发生。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `920100002` | `telemetry_degradation` | 机箱管理控制器 (CMC) 未监控指定的传感器。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `920100003` | `fault_log` | HD400 驱动器抽屉已打开，5 分钟服务窗口计时器已启动。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `920100004` | `fault_log` | 有多处风扇故障。 5 分钟驱动器断电警告。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `920100005` | `fault_log` | 其中一个手提箱风扇托架中的一个风扇发生故障。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `920100006` | `fault_log` | 节点上的传感器指示温度升高。驱动器过热。节点将立即重新启动。驱动电源将在五分钟后停止。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `920100007` | `fault_log` | 节点中的所有驱动器均已断电。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `920100008` | `fault_log` | 其中一个驱动器过热。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `920100009` | `fault_log` | 其中一个驱动器过热。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `930100000` | `fault_log` | 传感器报告的风扇值超出预期规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `930100001` | `fault_log` | 传感器报告的电气值超出预期规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `930100002` | `fault_log` | 传感器报告的温度值超出预期规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `930100003` | `fault_log` | 传感器报告的电气值超出预期规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `930100004` | `fault_log` | 传感器报告的电气值超出预期规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `930100005` | `fault_log` | 传感器报告的值超出预期规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `930100006` | `fault_log` | 传感器报告的值超出预期规格。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `940100001` | `fault_log` | OneFS {版本} 当前正在运行，但此硬件不支持。不受支持的 OneFS 版本。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `940100002` | `fault_log` | OneFS {version} 当前正在不受支持的节点 (devid(s) {devid}) 上运行。 {消息}。 | `reviewed` | PowerScale OneFS Event Reference Guide, October 2021 | [官方文档](<https://dl.dell.com/content/docu96961>) |
| `HW_POWEREDGE_IDRAC_MGMT_SERVICE` | `unknown` | 未收录的厂商事件代码 | `pending` | — | — |
| `QUOTA_NOTIFY_FAILED` | `unknown` | 未收录的厂商事件代码 | `pending` | — | — |
| `QUOTA_THRESHOLD_VIOLATION` | `unknown` | 未收录的厂商事件代码 | `pending` | — | — |
| `SW_ACCOUNT_UPDATED` | `unknown` | 未收录的厂商事件代码 | `pending` | — | — |
| `SW_CELOG_HEARTBEAT` | `unknown` | 未收录的厂商事件代码 | `pending` | — | — |
| `SW_JOBENG_JOB_PHASE_BEGIN` | `unknown` | 未收录的厂商事件代码 | `pending` | — | — |
| `SW_JOBENG_JOB_PHASE_END` | `unknown` | 未收录的厂商事件代码 | `pending` | — | — |
| `SW_JOBENG_JOB_STATE` | `unknown` | 未收录的厂商事件代码 | `pending` | — | — |
| `SW_JOBENG_JOBSCHED_NOT_STARTED` | `unknown` | 未收录的厂商事件代码 | `pending` | — | — |
| `SW_LICENSE_ENTITLEMENTS_EXCEEDED` | `unknown` | 未收录的厂商事件代码 | `pending` | — | — |
| `SW_SECURITY_VERIFICATION_FAILURE` | `unknown` | 未收录的厂商事件代码 | `pending` | — | — |
| `SW_SECURITY_VERIFICATION_SUCCESS` | `unknown` | 未收录的厂商事件代码 | `pending` | — | — |
| `SYS_NVME_PCI_LINK_ERROR` | `unknown` | 未收录的厂商事件代码 | `pending` | — | — |
| `SYS_PCI_AER` | `unknown` | 未收录的厂商事件代码 | `pending` | — | — |
