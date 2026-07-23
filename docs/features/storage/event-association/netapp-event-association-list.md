# NetApp ONTAP 事件关联信息清单

本清单由 `backend/scripts/initialize_vendor_event_definitions.py` 中的初始化目录生成，共 `199` 条；所有内置定义初始化时均为启用状态。

关联类型和审核边界见[厂商事件关联目录](overview.md)，待审核项的补证要求见[待核验厂商事件清单](unverified-code-list.md)。

| 事件代码 | 关联类型 | 中文标题 | 审核状态 | 适用版本 | 官网依据 |
| --- | --- | --- | --- | --- | --- |
| `arw.volume.state` | `system_activity` | 卷防勒索软件状态变更 | `reviewed` | ONTAP 9.14.1 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/arw-volume-events.html>) |
| `asup.aods.response.timeOut` | `telemetry_degradation` | AutoSupport OnDemand 响应超时 | `reviewed` | ONTAP 9.11.1–9.18.1 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems/asup-aods-events.html>) |
| `asup.post.drop` | `telemetry_degradation` | AutoSupport 消息投递失败 | `reviewed` | ONTAP 9.16.1 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9161/asup-post-events.html>) |
| `callhome.management.log` | `system_activity` | 管理日志 CallHome | `reviewed` | ONTAP 9.14.1 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/callhome-management-events.html>) |
| `callhome.performance.data` | `system_activity` | 性能数据 CallHome | `reviewed` | ONTAP 9.16.1 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9161/callhome-performance-events.html>) |
| `callhome.raid.no.recover` | `fault_log` | RAID 不可恢复错误 CallHome | `reviewed` | ONTAP EMS 当前文档 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems/callhome-raid-events.html>) |
| `ccma.quota.throughput` | `telemetry_degradation` | 性能归档保留空间不足 | `reviewed` | ONTAP 9.14.1、9.18.1 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems/ccma-quota-events.html>) |
| `configbr.backupCompleted` | `system_activity` | 配置备份完成 | `reviewed` | ONTAP EMS 当前文档 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems/configbr-backupcompleted-events.html>) |
| `disk.ddr.scan.start` | `unknown` | 未收录的厂商事件代码 | `pending` | — | — |
| `disk.ddr.scan.summary` | `unknown` | 未收录的厂商事件代码 | `pending` | — | — |
| `disk.max.partitions` | `fault_log` | 系统已达到最大分区磁盘数 | `reviewed` | ONTAP 9.14.1 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/disk-max-events.html>) |
| `disk.min.OS.error` | `fault_log` | 磁盘要求的 ONTAP 版本过高 | `reviewed` | ONTAP 9.14.1 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/disk-min-events.html>) |
| `disk.partition.exceeded` | `fault_log` | 磁盘分区数量超限 | `reviewed` | ONTAP 9.14.1 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/disk-partition-events.html>) |
| `fp.est.scan.catalog.updated` | `system_activity` | 空间效率估算目录已更新 | `reviewed` | ONTAP 9.18.1 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9181/fp-est-events.html>) |
| `kern.uptime.filer` | `system_activity` | 控制器运行状态周期记录 | `reviewed` | ONTAP 9.10.1、9.14.1、9.16.1、9.18.1 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems/kern-uptime-events.html>) |
| `license.check.ok` | `unknown` | 未收录的厂商事件代码 | `pending` | — | — |
| `mhost.ca.connect.cert.error` | `fault_log` | 证书连接错误 | `reviewed` | ONTAP EMS 当前文档 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems/mhost-ca-events.html>) |
| `mhost.ca.connect.delete` | `system_activity` | CA 连接删除 | `reviewed` | ONTAP EMS 当前文档 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems/mhost-ca-events.html>) |
| `mhost.ca.connect.failure` | `fault_log` | CA 连接失败 | `reviewed` | ONTAP EMS 当前文档 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems/mhost-ca-events.html>) |
| `monitor.volumes.one.ok` | `unknown` | 未收录的厂商事件代码 | `pending` | — | — |
| `nblade.execsOverLimit` | `performance_anomaly` | NFS 请求并发超过连接阈值 | `reviewed` | ONTAP 9.10.1–9.18.1 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems/nblade-execsoverlimit-events.html>) |
| `nis.group.db.build.success` | `system_activity` | NIS 组数据库构建成功 | `reviewed` | ONTAP 9.10.1–9.18.1 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems/nis-group-events.html>) |
| `quota.exceeded` | `unknown` | 未收录的厂商事件代码 | `pending` | — | — |
| `quota.normal` | `unknown` | 未收录的厂商事件代码 | `pending` | — | — |
| `quota.push.rules.complete` | `system_activity` | 配额规则推送完成 | `reviewed` | ONTAP 9.17.1 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9171/quota-push-events.html>) |
| `quota.push.rules.start` | `system_activity` | 配额规则推送开始 | `reviewed` | ONTAP 9.17.1 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9171/quota-push-events.html>) |
| `quota.resize.start` | `system_activity` | 配额调整开始 | `reviewed` | ONTAP 9.11.1 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9111/quota-resize-events.html>) |
| `quota.resize.stop` | `system_activity` | 配额调整停止 | `reviewed` | ONTAP 9.11.1 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9111/quota-resize-events.html>) |
| `quota.softlimit.exceeded` | `capacity_threshold` | 配额软限制超过 | `reviewed` | ONTAP EMS 当前文档 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems/quota-softlimit-events.html>) |
| `quota.softlimit.normal` | `system_activity` | 配额软限制恢复正常 | `reviewed` | ONTAP EMS 当前文档 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems/quota-softlimit-events.html>) |
| `raid.aggr.log.CP.count` | `unknown` | 未收录的厂商事件代码 | `pending` | — | — |
| `raid.aggrvote.updateNotOk` | `fault_log` | RAID：对 RDB 的镜像投票更新失败，聚合 UUID %s 出现错误 %s（丛数 %d；ID：%d、%d） | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.assim.disk.badlabelversion` | `fault_log` | %s 有 %s RAID 标签，版本为 (%d)，该标签不在当前支持的范围内 (%d - %d) | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.assim.disk.broken` | `fault_log` | 同化过程中检测到损坏的 %s | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.assim.disk.brokenPreAssim` | `fault_log` | 同化前检测到损坏的 %s | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.assim.disk.nolabels` | `fault_log` | %s 没有有效标签 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.assim.disk.region.hole` | `capacity_threshold` | 磁盘 %s (S/N %s) 在区域 %d（类型 %s，起始 %llu，大小 %llu）和区域 %d（类型 %s，起始 %llu，大小 %llu）之间的分配空间中存在漏洞 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.assim.disk.region.overlap` | `fault_log` | 在磁盘 %s (S/N %s) 上，区域 %d（类型 %s，起始位置 %llu，大小 %llu）与区域 %d（类型 %s，起始位置 %llu，大小 %llu）重叠 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.assim.fatal` | `fault_log` | 同化失败：%s | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.assim.fatal.upgrade` | `fault_log` | 同化失败：此系统似乎是从以前版本的 Data ONTAP 升级的 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.assim.label.makeForeignVol` | `fault_log` | %s %s 无法转换为 %snative 聚合；它会显得很陌生 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.assim.label.upgrade.corruptSize` | `fault_log` | 磁盘 %s 的旧标签已损坏：大小 [%d] 为 %u | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.assim.label.upgrade.parityMismatch` | `fault_log` | 磁盘 %s 的旧标签已损坏：奇偶校验类型不匹配 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.assim.rg.dupChildId` | `fault_log` | %s %s%s，rgobj_verify：RAID 对象 %d 具有 ID 为 %d 的重复子对象（%s 和 %s） | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.assim.tree.degradedDirty` | `fault_log` | %s“%s%s”已降级并且具有脏奇偶校验 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.assim.tree.dupId` | `fault_log` | %s %s%s 和 %s %s%s 具有相同的 RAID 树 ID | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.assim.tree.foreign` | `fault_log` | raidtree_verify：%s %s 是外部聚合，正在脱机 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.assim.tree.multipleRootVols` | `fault_log` | 卷 %s 和卷 %s 都声称是 %sroot 卷 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.assim.tree.noRootVol` | `fault_log` | 未找到可用的 %sroot 卷！ | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.assim.tree.tooManyChild` | `fault_log` | %s %s%s，raidtree_verify：Raidtree 有多个根对象 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.assim.upgrade.aggr.fail` | `fault_log` | %s %s%s 的 RAID 标签升级失败 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.autoPart.disabled` | `capacity_threshold` | 此系统上禁用磁盘自动分区：%s | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.carrier.remove` | `fault_log` | 在托架中的所有其他磁盘都出现故障后，%s 也出现故障 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.cksum.bad.file.block` | `fault_log` | 正在读取 %s %s%s、%s、磁盘块 %llu、%s inode 号 %d、snpid %d、文件块 %llu、级别 %d 上的坏块 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.cksum.ignore.file.bno` | `fault_log` | %s %s %s、%s 上的块号不匹配，stored_dbn = %u，expected_dbn = %llu； stored_vbn = %llu，expected_vbn = %llu，%s inode 号 %d，snpid %d，文件块 %llu，级别 %d | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.cksum.ignore.file.embed` | `fault_log` | %s %s %s、%s、磁盘块 %llu、%s inode 号 %d、snpid %d、文件块 %llu、级别 %d 上的校验和条目无效 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.cksum.replay.bad.entry` | `fault_log` | 跳过 NVRAM 中的 %d 个错误校验和条目 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.cksum.unverify.file.block` | `fault_log` | 正在读取 %s %s%s、%s、磁盘块 %llu、%s inode 号 %d、snpid %d、文件块 %llu、级别 %d 上的未验证块 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.cksum.wc.sblkErr` | `fault_log` | 由于 %s %s%s、%s 上的超级块 %llu 的 WAFL 上下文不匹配，导致校验和错误 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.config.check.failed` | `fault_log` | %s %s%s：所有 plex 均已失败 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.config.check.failedPlex` | `fault_log` | Plex %s%s 失败 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.config.check.offlinePlex` | `fault_log` | Plex %s%s 离线 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.config.disk.failed` | `fault_log` | %s 失败 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.config.filesystem.disk.failed` | `fault_log` | 文件系统 %s 失败 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.config.filesystem.disk.failed.after.copy` | `fault_log` | 文件系统 %s 在成功复制到替换系统后出现故障 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.config.online.notComp` | `fault_log` | %s %s%s 正在脱机 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.config.online.notCompressComp` | `fault_log` | 卷“%s%s”正在脱机，因为它已被压缩，并且容器使用自适应存储效率，而此版本的 Data ONTAP 不支持该效率 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.config.online.req.badvers` | `fault_log` | 此版本的 Data ONTAP 无法识别 %s %s%s 的文件系统 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.config.online.req.corrupt4` | `fault_log` | %s %s%s 不一致 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.config.online.req.inconsist` | `fault_log` | 由于中止的 vol 复制或 aggr 复制副本或中止的 snapmirror 初始（级别 0）传输，%s %s%s 处于不一致状态 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.config.online.req.mt.iv` | `fault_log` | 与镜像卷 %s %s%s 关联的镜像类型无效 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.config.online.req.nospace` | `capacity_threshold` | 包含聚合没有足够的空间来允许 %s 联机 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.config.online.req.unsup` | `fault_log` | 此 Data ONTAP 部署不支持“%s %s”的文件系统 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.config.rg.size.reminder` | `fault_log` | 卷 %s%s 的 raid 组大于 raid4 raidtype 的限制（最大 raid 组大小：%d，限制为 %d） | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.config.spare.disk.failed` | `fault_log` | 备用 %s 失败 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.data.lw.recFail` | `fault_log` | 由于 %s%s 上出现 %d 个丢失写入错误 %s 超过阈值，建议磁盘发生故障 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.disk.illegalAttach` | `fault_log` | %s 被非法附加 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.disk.io.toFailedDisk` | `fault_log` | DBG：%s 正在尝试 I/O 失败 %s | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.disk.mcc.mismatch` | `fault_log` | 磁盘 %s 以前属于启用 MetroCluster 的系统 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.disk.owner.change.fail` | `fault_log` | RAID 发起的所有权更改请求失败（聚合：%s 错误：%s） | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.disk.predictiveFailure` | `fault_log` | %s 报告了预测失败并且已失败；它将被复制到备用并失败 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.disk.replace.job.failed` | `fault_log` | 无法将磁盘 %s 替换为磁盘 %s | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.disk.tooBig.all.reminder` | `capacity_threshold` | 系统容量 %s 超出了 %s 支持的最大磁盘容量 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.diskadd.abort` | `fault_log` | 向 %s %s%s 添加磁盘已中止 %s | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.diskadd.add.abort` | `fault_log` | 由于 %s 出现故障，向 %s %s%s 添加磁盘已中止 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.diskadd.create.abort` | `fault_log` | 由于 %s 失败，%s %s%s 的创建中止 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.disktoc.tooRecent` | `fault_log` | %s 的磁盘目录版本 (%d) 比当前支持的版本 (%d) 更新 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.encrypt.disabled` | `fault_log` | 由于系统不符合 FIPS 标准，因此 RAID 加密不可用 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.encrypt.no.key` | `fault_log` | 由于错误“%d”，没有可用于卷“%s”的加密密钥 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.fdr.full` | `fault_log` | 磁盘注册表已满失败！ %s 型号 %s 的回收条目（序列号 %s） | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.fdr.reminder` | `fault_log` | 失败的 %s 仍然存在于系统中，应将其删除 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.fm.disasterSummary` | `fault_log` | RAID 灾难接管摘要：伙伴卷和聚合的数量=%d，rewrite-fsid 伙伴卷和聚合的数量=%d，过期的伙伴卷和聚合的数量=%d，忽略的伙伴卷和聚合的数量=%d，本地卷和聚合的数量=%d，过期的本地卷和聚合的数量=%d | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.fm.takeoverFail` | `fault_log` | RAID 接管失败：%s | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.fm.volDisasterBadState` | `fault_log` | 合作伙伴卷 %s 身份在 HA 灾难接管期间未更改：状态错误 %s | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.fm.volDisasterFail` | `fault_log` | 合作伙伴卷 %s HA 灾难接管错误 (%s)：%s | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.fm.volDisasterIgnore` | `fault_log` | 合作伙伴卷 %s 身份在 HA 接管期间未更改：%s | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.fm.volDisasterWarn` | `fault_log` | 合作伙伴卷 %s HA 灾难接管警告 (%s)：%s 卷接管可能不完整，客户端可能会看到过时的数据 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.fm.volFsidRewrite` | `fault_log` | 合作伙伴 %s %s FSID 在 HA 灾难接管期间被重写 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.fm.volFsidRewriteOod` | `fault_log` | 伙伴卷 %s FSID 在 HA 灾难接管期间被重写 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.hybrid.SSDHAExceed` | `fault_log` | 此节点及其伙伴 %s 上混合聚合的所有 SSD 磁盘大小总和超过 %s | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.hybrid.SSDTotExceed` | `fault_log` | 混合聚合 %s 的 SSD 磁盘大小总和超过 %s 最大值 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.mcc.heal.aggrs.canceled` | `fault_log` | 驻留在 %s 上的聚合 %s 是 %s，正在取消修复聚合操作 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.mcc.heal.roots.canceled` | `fault_log` | 聚合 %s 正忙于另一个配置操作 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.mcc.ISL.down` | `fault_log` | 由于远程站点存储不可见，%s 已取消；交换机间链路可能已关闭 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.mcc.nso.canceled` | `fault_log` | 聚合 %s 为 %s，正在取消协商切换 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.mcc.nso.dr.leftbehind` | `fault_log` | 切回操作留下了聚合 %s，从而取消了协商的切换 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.mcc.nso.ha.leftbehind` | `fault_log` | 交还操作留下了聚合 %s，从而取消了协商的切换 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.mcc.remote.storage.down` | `fault_log` | 由于远程站点存储不可见，%s 已取消； FC 或 SAS 链路可能已关闭 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.mcc.root.configError` | `fault_log` | 在根聚合中，%s | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.mcc.root.unmirrored` | `fault_log` | 根聚合未镜像 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.mcc.switchbackCanceled` | `fault_log` | DR 聚合 %s 为 %s，正在取消切回 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.mirror.bigio.restrict` | `fault_log` | %s %s 受到限制 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.mirror.bigio.restrict.failed` | `fault_log` | 无法限制 %s %s (%s) | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.mirror.bigio.wafliron.nostart` | `fault_log` | Wafliron 无法在 %s %s (%s) 上启动 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.mirror.faultIsolation.reminder` | `fault_log` | %s %s 个 plex 未进行故障隔离 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.mirror.lowSnapReserve` | `capacity_threshold` | SyncMirror %s“%s%s”中的聚合 Snapshot 副本保留太低 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.mirror.resync.snapcrtfail` | `fault_log` | %s %s%s：无法创建镜像重新同步快照副本 %s (%s) | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.mirror.snapDel.degraded` | `capacity_threshold` | 当聚合发生镜像降级时，正在删除 %s“%s%s”中的 SyncMirror 聚合 Snapshot 副本 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.mirror.snapDel.normal` | `capacity_threshold` | 正在删除 %s“%s%s”中的 SyncMirror 聚合 Snapshot 副本 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.mirror.snapEst.degraded` | `capacity_threshold` | SyncMirror %s“%s%s”镜像已降级 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.mirror.snapResExpand.failed` | `capacity_threshold` | 尝试将 SyncMirror %s“%s%s”中的聚合 Snapshot 副本保留从 %d%% 增加到 %d%% 失败 (%s) | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.mirror.verify.snapcrtfail` | `capacity_threshold` | %s %s%s：无法创建镜像验证快照副本 %s (%s) | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.mirror.vote.noRecord1Plex` | `fault_log` | 警告：%s %s%s 中只有一个 plex 可用 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.mirror.vote.sbFailed` | `fault_log` | 尝试切回操作时无法通过集群间网络与 DR 节点进行通信 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.mirror.vote.xferFailed` | `fault_log` | 由于 %s，在交还或聚合重新定位期间迁移聚合“%s”（UUID：%s）时，无法通过群集网络与目标节点进行通信 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.monitor.maxVols` | `fault_log` | 警告：主机上的卷过多 (%d) | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.multierr.bad.block` | `fault_log` | 将“%s%s”、块号 %llu、卷块号 %llu 标记为坏块 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.multierr.unverified.blk` | `fault_log` | 将“%s%s”、块号 [%llu - %llu]、卷块号 [%llu - %llu] 标记为未经验证的块 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.mv.defVol.online.fail` | `fault_log` | RAID：无法使聚合 %s 联机，因为 %s | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.no.parity.aggr` | `fault_log` | 聚合“%s”不使用任何 RAID 级别的数据保护；任何数据都不受保护 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.plex.faultIsolation.reminder` | `fault_log` | Plex %s 具有来自混合池的磁盘：%s | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.pmdOpt.misconfigured` | `fault_log` | 选项 raid.panic.missing.disks 设置为 %d，但在引导期间它将具有值 %d | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.pmdOpt.set` | `fault_log` | 选项 raid.panic.missing.disks 设置为当错误影响 %d 个或更多文件系统磁盘时发生紧急情况并停止设备 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.pmdOpt.singleDisk` | `fault_log` | 选项“raid.panic.missing.disks”设置为 1，这会导致系统在出现任何磁盘故障时出现紧急情况并停止 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.poolsort.disks_per_shelf` | `fault_log` | 通道 %s 上的架 ID %d 报告磁盘数量过多 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.rg.bigio.fatal` | `fault_log` | %s：长时间运行的 raid I/O 操作遇到致命的多磁盘错误 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.rg.diskcopy.mismatch` | `fault_log` | %s%s：匹配的磁盘不可用于复制磁盘 %s；使用磁盘 %s %s | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.rg.diskcopy.recom.fail` | `fault_log` | 超过磁盘复制错误阈值后，%s 建议失败 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.rg.readerr.bad.file.block` | `fault_log` | 正在读取 %s %s%s、%s inode 编号 %d、snpid %d、文件块 %llu、级别 %d 上的坏块 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.rg.readerr.block.fail` | `fault_log` | 无法在 %s%s 上正确恢复块 #%llu | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.rg.readerr.recommend.failure` | `fault_log` | 由于 %s%s、块 #%llu 上重复读取错误而导致磁盘故障 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.rg.readerr.wc.blkErr` | `fault_log` | 由于 %s %s%s、%s inode 号 %d、snapi %d、文件块 %llu、级别 %d、RBN %llu 上的 wafl 上下文不匹配，出现校验和错误 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.rg.recons.block.fail` | `fault_log` | 块 #%llu 无法在 %s%s 上正确重建 - 该块将被清零 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.rg.recons.cantStart` | `fault_log` | 无法在 RAID 组 %s%s 中开始重建：%s | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.rg.recons.disabled` | `fault_log` | 需要对 RAID 组 %s%s 执行重建，但重建被禁用 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.rg.recons.media.err.bypass` | `fault_log` | 已启用介质错误旁路，正在将磁盘 %s%s 的块 %llu 归零 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.rg.recons.mismatch` | `fault_log` | %s%s：匹配的磁盘不可用于重建；使用磁盘 %s %s | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.rg.recons.multidisk.fail` | `fault_log` | %s%s：无法从多磁盘错误中恢复 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.rg.spares.low` | `fault_log` | %s | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.root.unmirrored` | `fault_log` | 根卷未镜像 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.root.vol.noFaultIsolation` | `fault_log` | 根卷 %s%s：如果根卷升级为镜像，当前 plex 将具有来自混合池的磁盘 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.sp.create.failure` | `fault_log` | 存储池 %s 未成功创建 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.sp.unlock.failed` | `fault_log` | 无法解锁存储池 %s | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.stripe.replay.bad.block` | `fault_log` | NVRAM 中的坏块缓冲区条目 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.stripe.replay.bad.checksum` | `fault_log` | NVRAM 中的校验和错误 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.stripe.replay.bad.key` | `fault_log` | 条带 %llu：无法使用 %s %s 中的密钥 %d 找到 NVRAM 插槽 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.stripe.replay.bad.stripe` | `fault_log` | NVRAM 中的条带条目错误 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.stripe.replay.pzero.mismatch` | `fault_log` | 在 NVRAM 中检测到 %s %s 中条带 %llu 的奇偶校验块校验和不匹配 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.switchoverFail` | `fault_log` | 切换同化失败：%s | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.syncmirr.at.IOrecovery` | `fault_log` | 由于错误状态 %s，预计 plex %s 上的 I/O 服务时间会更长 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.syncmirror.agrsv.to` | `fault_log` | 磁盘驱动程序使属于 SyncMirror plex %s 的 %s%s 的 I/O 严重超时 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.syncmirror.at.degraded` | `fault_log` | %s%s [UUID:%s] 已镜像，并且 %s plex 处于脱机状态 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.uninitialized.parity.vol` | `capacity_threshold` | • 警告 * %s %s%s 创建时没有奇偶校验；不要让其数据磁盘出现故障！ | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.unsupported.bitformat` | `fault_log` | %s 上的标签表明该磁盘属于 32 位聚合，但已弃用该聚合 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.unsupported.cksumtype` | `fault_log` | %s 上的标签指示该磁盘属于 ZCS 聚合，但已弃用该聚合 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.vol.inconsist.unmount` | `fault_log` | 不一致的 %s %s%s 已卸载 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.vol.mirror.degraded` | `fault_log` | %s %s%s 已镜像，并且一个 plex 发生故障 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.vol.noMirrorSupport` | `fault_log` | 镜像%s %s%s 受到限制，系统不支持SyncMirror | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.vol.online.req.giveback` | `fault_log` | 使“%s %s”联机失败，因为交还正在进行中 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.vol.online.req.nso` | `fault_log` | 无法使卷“%s”联机，因为 MetroCluster 协商切换源操作正在进行中 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.vol.online.req.relocate` | `fault_log` | 使灵活卷“%s”联机失败，因为“存储聚合重定位”操作正在进行中 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.vol.online.req.sb` | `fault_log` | 无法使卷“%s”联机，因为 MetroCluster 切回操作正在进行 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.vol.root.noMirrorSupport` | `fault_log` | %s 聚合已镜像，但系统不支持 SyncMirror | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.vol.rootRestrictLessRecent` | `fault_log` | 卷 %s%s 由于创建时间较新而受到限制 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.vol.rootSelectMostRecent` | `fault_log` | 卷 %s%s 根据其最近的创建时间被选为默认根卷 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.vol.tooBig.allp.reminder` | `fault_log` | 所有聚合 plex 大小的总和为 %s，超出了 %s 最大值 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.vol.tooBig.allv.reminder` | `fault_log` | 所有聚合大小的总和为 %s，超出了 %s 最大值 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.vol.tooBig.ha.reminder` | `fault_log` | 所有聚合大小的总和为 %s，超过 %s（HA 对中最大值的一半） | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.vol.tooBig.offline` | `fault_log` | %s %s%s 无法联机，因为它的大小 %s 大于允许的最大值 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.vol.tooBig.reminder` | `fault_log` | %s%s %s 的 %s 大小超出限制 %s | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.vol.unprotected.remotesyncmirror` | `fault_log` | %s %s%s 已镜像，但其中一个 plex 未在线 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.vol.volinfo.mismatch` | `fault_log` | %s %s%s：volinfo 块 (VBN %llu) 在两个 plex 中不匹配 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `raid.warn.no.sparecore.disk` | `fault_log` | 节点上没有合适的备用磁盘可用于将来可能的核心转储操作 | `reviewed` | ONTAP 9.14.1 RAID EMS reference | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html>) |
| `secd.authsys.lookup.failed` | `fault_log` | UNIX 用户凭据查询失败 | `reviewed` | ONTAP 9.11.1–9.18.1 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems/secd-authsys-events.html>) |
| `sis.auto.session.change` | `system_activity` | 后台去重会话数因负载调整 | `reviewed` | ONTAP 9.10.1–9.18.1 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems/sis-auto-events.html>) |
| `tsse_compression_done` | `unknown` | 未收录的厂商事件代码 | `pending` | — | — |
| `wafl.analytics.enterOverload` | `telemetry_degradation` | 文件系统分析进入过载 | `reviewed` | ONTAP EMS 当前文档 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems/wafl-analytics-events.html>) |
| `wafl.analytics.exitOverload` | `system_activity` | 文件系统分析退出过载 | `reviewed` | ONTAP EMS 当前文档 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems/wafl-analytics-events.html>) |
| `wafl.compress.cde.event` | `system_activity` | 压缩数据效率事件 | `reviewed` | ONTAP 9.10.1 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9101/wafl-compress-events.html>) |
| `wafl.data.compaction.event` | `system_activity` | 数据压缩整理事件 | `reviewed` | ONTAP EMS 当前文档 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems/wafl-data-events.html>) |
| `wafl.inode.fill.enable` | `unknown` | 未收录的厂商事件代码 | `pending` | — | — |
| `wafl.quota.user.exceeded` | `capacity_threshold` | 用户配额超过 | `reviewed` | ONTAP EMS 当前文档 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems/wafl-quota-events.html>) |
| `wafl.rclm.est.scan.done` | `system_activity` | 空间回收估算扫描完成 | `reviewed` | ONTAP EMS 当前文档 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems/wafl-rclm-events.html>) |
| `wafl.scan.done` | `system_activity` | WAFL 扫描完成 | `reviewed` | ONTAP 9.11.1、9.18.1 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9181/wafl-scan-events.html>) |
| `wafl.scan.ownblocks.done` | `system_activity` | 归属块检查完成 | `reviewed` | ONTAP 9.11.1、9.18.1 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9181/wafl-scan-events.html>) |
| `wafl.scan.start` | `unknown` | 未收录的厂商事件代码 | `pending` | — | — |
| `wafl.spacemgmnt.policyChg` | `system_activity` | 空间管理策略变更 | `reviewed` | ONTAP 9.18.1 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9181/wafl-spacemgmnt-events.html>) |
| `wafl.vol.blks_used.done` | `system_activity` | 已用块计算完成 | `reviewed` | ONTAP 9.14.1、9.18.1 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9181/wafl-vol-events.html>) |
| `wafl.vol.snap_create.done` | `system_activity` | 快照创建扫描完成 | `reviewed` | ONTAP 9.14.1、9.18.1 | [官方文档](<https://docs.netapp.com/us-en/ontap-ems-9181/wafl-vol-events.html>) |
