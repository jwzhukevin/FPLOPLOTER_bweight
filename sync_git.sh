#!/bin/bash

# Git 同步脚本（SSH 专用）
# 作用：强制通过 SSH 与 GitHub 通信，确保提交与推送走 SSH 通道
# 使用方法：./sync_git.sh [提交信息]

# 设置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[信息]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[成功]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[警告]${NC} $1"
}

print_error() {
    echo -e "${RED}[错误]${NC} $1"
}

# 检查是否在 Git 仓库中
check_git_repo() {
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        print_error "当前目录不是 Git 仓库！"
        exit 1
    fi
}

# 确保远程使用 SSH
ensure_ssh_remote() {
    print_info "检查远程地址是否为 SSH..."
    if ! git remote get-url origin > /dev/null 2>&1; then
        print_error "未找到远程 origin，请先添加远程仓库（SSH 格式）"
        echo "示例: git remote add origin git@github.com:<OWNER>/<REPO>.git"
        exit 1
    fi

    current_url=$(git remote get-url origin)
    if [[ $current_url == https://github.com/* ]]; then
        ssh_url=$(echo "$current_url" | sed 's#https://github.com/#git@github.com:#')
        print_info "将远程从 HTTPS 转换为 SSH: $ssh_url"
        git remote set-url origin "$ssh_url"
        if [ $? -ne 0 ]; then
            print_error "设置 SSH 远程失败"
            exit 1
        fi
        print_success "已切换为 SSH: $(git remote get-url origin)"
    else
        print_success "远程已为 SSH: $current_url"
    fi
}

# 检查 SSH 连接
check_ssh_connection() {
    print_info "检查 SSH 连接到 GitHub..."
    # 成功时输出包含 successfully authenticated；失败时给出指导
    if ssh -T git@github.com 2>&1 | grep -q "successfully authenticated"; then
        print_success "SSH 连接正常"
        return 0
    else
        print_error "SSH 连接失败：请检查是否已配置 SSH Key 并添加到 GitHub"
        echo "排查步骤："
        echo "  1) 生成密钥（推荐 ed25519）：ssh-keygen -t ed25519 -C \"你的邮箱\""
        echo "  2) 查看公钥：cat ~/.ssh/id_ed25519.pub（或 id_rsa.pub）"
        echo "  3) 将公钥添加到 GitHub > Settings > SSH and GPG keys"
        echo "  4) 可选：eval \"\$(ssh-agent -s)\" && ssh-add ~/.ssh/id_ed25519"
        return 1
    fi
}

# 检查 Git 用户信息（用于提交关联）
check_git_config() {
    name=$(git config user.name)
    email=$(git config user.email)
    if [ -z "$name" ] || [ -z "$email" ]; then
        print_warning "未配置提交用户名或邮箱，将影响提交归属"
        echo "设置示例："
        echo "  git config --global user.name \"你的名字\""
        echo "  git config --global user.email \"你的邮箱\""
    else
        print_info "Git 用户: $name <$email>"
    fi
}

# 检查工作区状态
check_working_directory() {
    print_info "检查工作区状态..."
    
    # 检查是否有未跟踪的文件
    if [ -n "$(git ls-files --others --exclude-standard)" ]; then
        print_warning "发现未跟踪的文件："
        git ls-files --others --exclude-standard
        echo
    fi
    
    # 检查是否有修改的文件
    if [ -n "$(git diff --name-only)" ]; then
        print_warning "发现已修改但未暂存的文件："
        git diff --name-only
        echo
    fi
    
    # 检查是否有已暂存的文件
    if [ -n "$(git diff --cached --name-only)" ]; then
        print_info "已暂存的文件："
        git diff --cached --name-only
        echo
    fi
}

# 添加所有更改
add_all_changes() {
    print_info "添加所有更改到暂存区..."
    git add .
    
    if [ $? -eq 0 ]; then
        print_success "所有更改已添加到暂存区"
    else
        print_error "添加文件到暂存区失败"
        exit 1
    fi
}

# 提交更改
commit_changes() {
    local commit_message="$1"
    
    # 如果没有提供提交信息，使用默认信息
    if [ -z "$commit_message" ]; then
        commit_message="自动同步 - $(date '+%Y-%m-%d %H:%M:%S')"
    fi
    
    print_info "提交更改: $commit_message"
    git commit -m "$commit_message"
    
    if [ $? -eq 0 ]; then
        print_success "提交成功"
    else
        print_warning "没有新的更改需要提交"
    fi
}

# 推送到远程仓库
push_to_remote() {
    print_info "推送到远程仓库..."
    
    # 获取当前分支名
    current_branch=$(git branch --show-current)
    print_info "当前分支: $current_branch"
    
    # 尝试推送
    git push origin $current_branch
    
    if [ $? -eq 0 ]; then
        print_success "推送成功！"
    else
        print_error "推送失败！"
        print_info "尝试强制推送（谨慎使用）..."
        read -p "是否要强制推送？(y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git push --force origin $current_branch
            if [ $? -eq 0 ]; then
                print_success "强制推送成功！"
            else
                print_error "强制推送也失败了"
                exit 1
            fi
        else
            print_info "取消推送"
            exit 1
        fi
    fi
}

# 从远程仓库拉取更新
pull_from_remote() {
    print_info "从远程仓库拉取更新..."
    git pull origin $(git branch --show-current)
    
    if [ $? -eq 0 ]; then
        print_success "拉取成功"
    else
        print_warning "拉取失败或有冲突"
    fi
}

# 主函数
main() {
    print_info "开始 Git 同步流程..."
    echo "=================================="
    
    # 检查是否在 Git 仓库中
    check_git_repo
    
    # 检查工作区状态
    check_working_directory

    # 远程必须为 SSH
    ensure_ssh_remote

    # 必须通过 SSH 验证成功
    if ! check_ssh_connection; then
        exit 1
    fi

    # 提示 Git 提交身份
    check_git_config
    
    # 先尝试拉取远程更新
    pull_from_remote
    
    # 添加所有更改
    add_all_changes
    
    # 提交更改
    commit_changes "$1"
    
    # 推送到远程仓库
    push_to_remote
    
    echo "=================================="
    print_success "Git 同步完成！"
}

# 运行主函数，传递第一个参数作为提交信息
main "$1"
