# 错误码对照表

> 本文档由脚本自动生成，基于 `app/error_messages.json`。
> 如需修改错误文案或新增错误码，请修改 `app/error_messages.json`，然后运行脚本重新生成。
> 生成时间：2026-02-20 17:10:02

## 模块 admin

| 错误码 | Key | 中文提示 |
|--------|-----|----------|
| `12000` | `ADMIN_ROLE_INVALID` | 角色选择不合法，请在用户、审核员、管理员中选择。 |
| `12001` | `ADMIN_CANNOT_EDIT_SELF_ROLE` | 不能修改当前登录账号的角色。 |
| `12002` | `ADMIN_SUPER_ONLY_EDIT_ADMIN` | 只有超级管理员可以修改管理员或超级管理员的角色。 |
| `12003` | `ADMIN_SUPER_ONLY_CREATE_ADMIN` | 只有超级管理员可以任命管理员。 |
| `12004` | `ADMIN_LAST_ADMIN_CANNOT_DELETE` | 系统中至少需要保留一名管理员，无法删除最后一个管理员。 |
| `12005` | `ADMIN_INVALID_MUTE_DURATION` | 禁言时长设置不合法，请检查后重新选择。 |
| `12006` | `ADMIN_CANNOT_MUTE_SELF` | 不能对当前登录账号进行禁言操作。 |
| `12007` | `ADMIN_CANNOT_MUTE_PEER_ADMIN` | 普通管理员不能禁言其它管理员或超级管理员。 |
| `12008` | `ADMIN_CANNOT_DELETE_SELF` | 不能删除当前登录账号。 |
| `12009` | `ADMIN_CANNOT_DELETE_PEER_ADMIN` | 普通管理员不能删除其它管理员或超级管理员账号。 |
| `12010` | `ADMIN_CANNOT_BAN_SELF` | 不能封禁当前登录账号。 |
| `12011` | `ADMIN_CANNOT_BAN_PEER_ADMIN` | 普通管理员不能封禁其它管理员或超级管理员账号。 |
| `12012` | `ADMIN_INVALID_BAN_DURATION` | 封禁时长设置不合法，请检查后重新选择。 |
| `12013` | `ADMIN_CANNOT_UNBAN_PEER_ADMIN` | 普通管理员不能解封其它管理员或超级管理员账号。 |
| `12014` | `ADMIN_USERNAME_REQUIRED` | 请填写用户名。 |
| `12015` | `ADMIN_EMAIL_REQUIRED` | 请填写邮箱地址。 |
| `12016` | `ADMIN_PASSWORD_REQUIRED` | 请设置登录密码。 |
| `12017` | `ADMIN_SUPER_ONLY_CREATE_ADMIN_ACCOUNT` | 只有超级管理员可以创建管理员账号。 |
| `12018` | `ADMIN_PASSWORD_MIN_LENGTH` | 密码长度至少需要 8 位。 |
| `12019` | `ADMIN_PASSWORD_COMPLEXITY` | 密码需同时包含字母和数字，请重新设置。 |

## 模块 auth

| 错误码 | Key | 中文提示 |
|--------|-----|----------|
| `10001` | `AUTH_INVALID_JSON` | 请求数据格式不正确，请检查后重试。 |
| `10002` | `AUTH_UNSUPPORTED_CONTENT_TYPE` | 当前请求格式不支持，请使用 JSON 或表单提交。 |
| `10003` | `AUTH_MISSING_CREDENTIALS` | 请输入用户名和密码后再尝试登录。 |
| `10004` | `AUTH_MISSING_REFRESH_TOKEN` | 刷新令牌缺失，请重新登录。 |
| `10005` | `AUTH_INVALID_EMAIL_FORMAT` | 邮箱格式不正确，请检查后重新输入。 |
| `10006` | `AUTH_REQUIRED_FIELDS_EMPTY` | 还有必填项未填写，请补充完整后再提交。 |
| `10007` | `AUTH_EMAIL_NOT_REGISTERED` | 该邮箱尚未注册，请先完成注册。 |
| `10008` | `AUTH_PASSWORD_TOO_SHORT` | 密码长度过短，请设置为至少 6 位。 |
| `10009` | `AUTH_INVALID_OR_EXPIRED_CODE` | 验证码错误或已失效，请重新获取。 |
| `10010` | `AUTH_PASSWORD_CONFIRM_MISMATCH` | 两次输入的密码不一致，请重新确认。 |
| `10011` | `AUTH_PASSWORD_SAME_AS_OLD` | 新密码不能与当前密码相同，请设置一个新密码。 |
| `10012` | `AUTH_LOGIN_ERROR` | 登录过程中出现异常，请稍后重试。 |
| `10013` | `AUTH_REFRESH_ERROR` | 刷新登录状态失败，请重新登录。 |
| `10014` | `AUTH_SEND_CODE_TOO_FREQUENT` | 验证码发送过于频繁，请稍后再试。 |
| `10015` | `AUTH_EMAIL_SMTP_CLOSED` | 邮件服务暂时不可用，请稍后再试或联系管理员。 |
| `10016` | `AUTH_EMAIL_AUTH_FAILED` | 邮件账号认证失败，请联系管理员检查邮箱配置。 |
| `10017` | `AUTH_EMAIL_TIMEOUT` | 连接邮件服务器超时，请稍后重试。 |
| `10018` | `AUTH_CHECK_REGISTER_INFO_ERROR` | 校验注册信息时发生错误，请稍后再试。 |
| `10019` | `AUTH_RESET_PASSWORD_EMAIL_ERROR` | 重置密码失败，请检查邮箱是否正确。 |
| `10020` | `AUTH_RESET_PASSWORD_ERROR` | 重置密码失败，请稍后重试。 |
| `10021` | `AUTH_REGISTER_SYSTEM_ERROR` | 注册失败，系统出现异常，请稍后重试。 |
| `10022` | `AUTH_REGISTER_USER_ERROR` | 用户注册失败，请稍后再试。 |
| `10023` | `AUTH_GET_USER_INFO_ERROR` | 获取用户信息失败，请稍后重试。 |
| `10024` | `AUTH_CHANGE_PASSWORD_ERROR` | 修改密码失败，请稍后重试。 |
| `10025` | `AUTH_SEND_CODE_ERROR` | 发送验证码失败，请稍后再试。 |
| `10026` | `AUTH_SEND_RESET_CODE_ERROR` | 发送重置密码验证码失败，请稍后再试。 |

## 模块 comment

| 错误码 | Key | 中文提示 |
|--------|-----|----------|
| `16001` | `COMMENT_TARGET_TYPE_INVALID` | 评论目标类型不合法，请刷新后重试。 |
| `16002` | `COMMENT_CONTENT_REQUIRED` | 评论内容不能为空。 |
| `16003` | `COMMENT_CONTENT_TOO_LONG` | 评论内容过长，请精简后再提交（最多 500 字）。 |
| `16004` | `COMMENT_TARGET_ID_REQUIRED` | 评论目标不存在或参数缺失，请刷新后重试。 |
| `16005` | `COMMENT_PARENT_NOT_FOUND` | 回复的上级评论不存在或已被删除。 |
| `16006` | `COMMENT_REACTION_ACTION_INVALID` | 不支持的评论操作类型，请刷新后重试。 |
| `16010` | `COMMENT_GET_LIST_ERROR` | 获取评论列表失败，请稍后再试。 |
| `16011` | `COMMENT_CREATE_ERROR` | 发表评论失败，请稍后重试。 |
| `16012` | `COMMENT_REACTION_ERROR` | 操作评论失败，请稍后再试。 |
| `16013` | `COMMENT_DELETE_ERROR` | 删除评论失败，请稍后重试。 |
| `16014` | `COMMENT_RESTORE_ERROR` | 恢复评论失败，请稍后再试。 |

## 模块 knowledge_base

| 错误码 | Key | 中文提示 |
|--------|-----|----------|
| `13001` | `KB_NAME_DESC_REQUIRED` | 请填写知识库名称和简介。 |
| `13002` | `KB_AT_LEAST_ONE_FILE` | 请至少上传一个文件到知识库。 |
| `13003` | `KB_NAME_DUPLICATED` | 你已经有一个同名知识库，请更换名称后重试。 |
| `13004` | `KB_NO_FIELDS_TO_UPDATE` | 没有可更新的内容，请修改后再提交。 |
| `13005` | `KB_NOT_FOUND` | 知识库不存在或已被删除。 |
| `13006` | `KB_UPLOAD_ERROR` | 上传知识库失败，请稍后重试。 |
| `13007` | `KB_GET_PUBLIC_ERROR` | 获取公开知识库失败，请稍后再试。 |
| `13008` | `KB_GET_DETAIL_ERROR` | 获取知识库详情失败，请稍后重试。 |
| `13009` | `KB_GET_USER_LIST_ERROR` | 获取个人知识库列表失败，请稍后再试。 |
| `13010` | `KB_ALREADY_PENDING` | 该知识库已处于待审核状态，无需重复提交。 |
| `13011` | `KB_CANNOT_RETURN_REJECTED` | 已被拒绝的知识库无法再次退回审核。 |
| `13012` | `KB_UNSTAR_ERROR` | 取消收藏知识库失败，请稍后再试。 |
| `13013` | `KB_UPDATE_ERROR` | 修改知识库失败，请稍后重试。 |
| `13014` | `KB_ADD_FILE_ERROR` | 向知识库添加文件失败，请稍后再试。 |
| `13015` | `KB_DELETE_FILE_ERROR` | 删除知识库文件失败，请稍后再试。 |
| `13016` | `KB_DOWNLOAD_FILE_ERROR` | 下载知识库文件失败，请稍后重试。 |
| `13017` | `KB_DELETE_ERROR` | 删除知识库失败，请稍后再试。 |

## 模块 message

| 错误码 | Key | 中文提示 |
|--------|-----|----------|
| `15001` | `MESSAGE_TITLE_REQUIRED` | 请填写消息标题。 |
| `15002` | `MESSAGE_CONTENT_REQUIRED` | 请填写消息内容。 |
| `15003` | `MESSAGE_BROADCAST_TYPE_INVALID` | 仅公告类型消息支持广播功能。 |
| `15004` | `MESSAGE_RECIPIENT_REQUIRED` | 请至少选择一位接收者。 |
| `15005` | `MESSAGE_NO_VALID_RECIPIENT` | 没有有效的接收者，请检查接收人列表。 |
| `15006` | `MESSAGE_PAGINATION_INVALID` | 分页参数不合法，请检查 page 与 page_size。 |
| `15007` | `MESSAGE_UPDATE_FIELDS_EMPTY` | 请至少修改标题、内容或简介中的一项。 |
| `15008` | `MESSAGE_PAGE_SIZE_INVALID` | 每页条数应在 1 到 100 之间。 |
| `15009` | `MESSAGE_PAGE_INVALID` | 页码必须大于等于 1。 |
| `15010` | `MESSAGE_ID_LIST_EMPTY` | 消息 ID 列表不能为空。 |
| `15020` | `MESSAGE_SEND_ERROR` | 发送消息失败，请稍后重试。 |
| `15021` | `MESSAGE_GET_DETAIL_ERROR` | 获取消息详情失败，请稍后再试。 |
| `15022` | `MESSAGE_GET_LIST_ERROR` | 获取消息列表失败，请稍后再试。 |
| `15023` | `MESSAGE_GET_BY_TYPE_ERROR` | 按类型获取消息列表失败，请稍后重试。 |
| `15024` | `MESSAGE_MARK_READ_ERROR` | 标记消息已读失败，请稍后再试。 |
| `15025` | `MESSAGE_DELETE_ERROR` | 删除消息失败，请稍后重试。 |
| `15026` | `MESSAGE_UPDATE_ERROR` | 更新消息失败，请稍后再试。 |
| `15027` | `MESSAGE_GET_BROADCAST_HISTORY_ERROR` | 获取公告历史失败，请稍后重试。 |
| `15028` | `MESSAGE_BATCH_DELETE_ERROR` | 批量删除消息失败，请稍后再试。 |

## 模块 persona

| 错误码 | Key | 中文提示 |
|--------|-----|----------|
| `14001` | `PERSONA_NOT_FOUND` | 人设卡不存在或已被删除。 |
| `14002` | `PERSONA_AT_LEAST_ONE_FILE` | 请至少上传一个人设相关文件。 |
| `14003` | `PERSONA_UPLOAD_ERROR` | 上传人设卡失败，请稍后重试。 |
| `14004` | `PERSONA_GET_PUBLIC_ERROR` | 获取公开人设卡失败，请稍后再试。 |
| `14005` | `PERSONA_GET_DETAIL_ERROR` | 获取人设卡详情失败，请稍后重试。 |
| `14006` | `PERSONA_CHECK_STAR_ERROR` | 检查人设卡收藏状态失败，请稍后再试。 |
| `14007` | `PERSONA_GET_USER_LIST_ERROR` | 获取个人人设卡列表失败，请稍后再试。 |
| `14008` | `PERSONA_UPDATE_ERROR` | 修改人设卡失败，请稍后重试。 |
| `14009` | `PERSONA_UNSTAR_ERROR` | 取消收藏人设卡失败，请稍后再试。 |
| `14010` | `PERSONA_ALREADY_PENDING` | 该人设卡已处于待审核状态，无需重复提交。 |
| `14011` | `PERSONA_CANNOT_RETURN_REJECTED` | 已被拒绝的人设卡无法再次退回审核。 |
| `14012` | `PERSONA_DELETE_ERROR` | 删除人设卡失败，请稍后再试。 |
| `14013` | `PERSONA_ADD_FILE_ERROR` | 向人设卡添加文件失败，请稍后再试。 |
| `14014` | `PERSONA_DELETE_FILE_ERROR` | 删除人设卡文件失败，请稍后再试。 |
| `14015` | `PERSONA_DOWNLOAD_FILE_ERROR` | 下载人设卡文件失败，请稍后重试。 |
| `14020` | `PERSONA_FILE_COUNT_INVALID` | 人设配置错误：必须且仅保留一个 bot_config.toml 文件。 |
| `14021` | `PERSONA_FILE_NAME_INVALID` | 人设配置错误：配置文件名必须为 bot_config.toml。 |
| `14022` | `PERSONA_FILE_TYPE_INVALID` | 人设配置错误：存在不支持的文件类型，请检查上传文件。 |
| `14023` | `PERSONA_FILE_SIZE_EXCEEDED` | 人设配置错误：文件体积过大，请压缩或拆分后再试。 |
| `14024` | `PERSONA_FILE_CONTENT_SIZE_EXCEEDED` | 人设配置错误：文件内容过大，请压缩或拆分后再试。 |
| `14025` | `PERSONA_TOML_VERSION_MISSING` | 人设配置错误：TOML 中缺少版本号字段，请补充后重试。 |
| `14026` | `PERSONA_TOML_PARSE_ERROR` | 人设配置错误：TOML 解析失败，请检查格式是否正确。 |

## 模块 user

| 错误码 | Key | 中文提示 |
|--------|-----|----------|
| `10100` | `USER_AVATAR_UPLOAD_ERROR` | 上传头像失败，请稍后重试。 |
| `10101` | `USER_AVATAR_DELETE_ERROR` | 删除头像失败，请稍后再试。 |
| `10102` | `USER_AVATAR_GET_ERROR` | 获取头像失败，请稍后重试。 |
| `10200` | `USER_GET_STARS_ERROR` | 获取收藏记录失败，请稍后重试。 |
| `10201` | `USER_GET_UPLOAD_HISTORY_ERROR` | 获取上传历史失败，请稍后再试。 |
| `10202` | `USER_GET_UPLOAD_STATS_ERROR` | 获取上传统计失败，请稍后重试。 |
| `10203` | `USER_GET_OVERVIEW_ERROR` | 获取个人数据概览失败，请稍后重试。 |
| `10204` | `USER_GET_TREND_ERROR` | 获取个人数据趋势失败，请稍后重试。 |

---

## 使用说明

### 添加新错误码

1. 编辑 `app/error_messages.json`，添加新的错误码条目：

```json
{
  "20001": {
    "key": "NEW_ERROR_KEY",
    "module": "new_module",
    "messages": {
      "zh-CN": "错误提示信息"
    }
  }
}
```

2. 运行脚本重新生成文档：

```bash
python scripts/generate_error_codes_doc.py
```

### 错误码规范

- **10000-10999**: 认证和用户相关错误
- **12000-12999**: 管理员相关错误
- **13000-13999**: 知识库相关错误
- **14000-14999**: 人设卡相关错误
- **15000-15999**: 消息相关错误
- **16000-16999**: 评论相关错误

### JSON 文件结构

```json
{
  "错误码": {
    "key": "错误码标识符",
    "module": "模块名称",
    "messages": {
      "zh-CN": "中文错误提示"
    }
  }
}
```

---

**最后更新**: 2026-02-20 17:10:02
