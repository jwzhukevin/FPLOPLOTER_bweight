#!/bin/bash

# Git 同步推送脚本
# 功能：语法检查 -> 虚拟环境激活 -> requirements.txt更新 -> 版本标记 -> 提交推送
# 使用方法：./push.sh

# 全局变量初始化
CURRENT_VERSION_TAG=""

# 设置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 打印带颜色的消息函数
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

print_step() {
    echo -e "${CYAN}[步骤]${NC} $1"
}

# 错误处理函数
handle_error() {
    print_error "$1"
    exit 1
}

# 检查命令是否存在
check_command() {
    if ! command -v "$1" &> /dev/null; then
        handle_error "命令 '$1' 未找到，请先安装"
    fi
}

# Python 语法检查函数
check_python_syntax() {
    print_step "开始检查 Python 文件语法..."
    
    local python_files=$(find . -name "*.py" -not -path "./FPLP/*" -not -path "./__pycache__/*" -not -path "./.git/*")
    local error_count=0
    
    if [ -z "$python_files" ]; then
        print_warning "未找到 Python 文件"
        return 0
    fi
    
    # 使用 python -m py_compile 检查语法
    for file in $python_files; do
        print_info "检查文件: $file"
        if ! python -m py_compile "$file" 2>/dev/null; then
            print_error "Python 语法错误: $file"
            python -m py_compile "$file"
            ((error_count++))
        fi
    done
    
    # 如果安装了 flake8，进行额外的代码质量检查
    if command -v flake8 &> /dev/null; then
        print_info "使用 flake8 进行代码质量检查..."
        for file in $python_files; do
            if ! flake8 "$file" --max-line-length=88 --ignore=E203,W503 2>/dev/null; then
                print_warning "代码风格建议: $file"
                flake8 "$file" --max-line-length=88 --ignore=E203,W503
            fi
        done
    fi
    
    if [ $error_count -gt 0 ]; then
        handle_error "发现 $error_count 个 Python 语法错误，请修复后重试"
    fi
    
    print_success "Python 文件语法检查通过"
}

# Bash 语法检查函数
check_bash_syntax() {
    print_step "开始检查 Bash 文件语法..."
    
    local bash_files=$(find . -name "*.sh" -not -path "./FPLP/*" -not -path "./.git/*")
    local error_count=0
    
    if [ -z "$bash_files" ]; then
        print_warning "未找到 Bash 文件"
        return 0
    fi
    
    for file in $bash_files; do
        print_info "检查文件: $file"
        if ! bash -n "$file" 2>/dev/null; then
            print_error "Bash 语法错误: $file"
            bash -n "$file"
            ((error_count++))
        fi
    done
    
    if [ $error_count -gt 0 ]; then
        handle_error "发现 $error_count 个 Bash 语法错误，请修复后重试"
    fi
    
    print_success "Bash 文件语法检查通过"
}

# 激活虚拟环境函数
activate_virtual_env() {
    print_step "激活虚拟环境 FPLP..."
    
    if [ ! -d "FPLP" ]; then
        print_warning "虚拟环境 FPLP 不存在，正在创建..."
        python -m venv FPLP
        if [ $? -ne 0 ]; then
            handle_error "创建虚拟环境失败"
        fi
    fi
    
    # 激活虚拟环境
    if [ -f "FPLP/Scripts/activate" ]; then
        # Windows 环境
        source FPLP/Scripts/activate
    elif [ -f "FPLP/bin/activate" ]; then
        # Linux/Mac 环境
        source FPLP/bin/activate
    else
        handle_error "无法找到虚拟环境激活脚本"
    fi
    
    print_success "虚拟环境已激活"
}

# 更新 requirements.txt 函数
update_requirements() {
    print_step "更新 requirements.txt 文件..."
    
    # 确保在虚拟环境中
    if [ -z "$VIRTUAL_ENV" ]; then
        print_warning "虚拟环境未激活，尝试重新激活..."
        activate_virtual_env
    fi
    
    # 生成新的 requirements.txt
    print_info "生成新的 requirements.txt..."
    pip freeze > requirements.txt
    
    # 检查是否有变化
    if git diff --quiet requirements.txt; then
        print_info "requirements.txt 无变化"
    else
        print_success "requirements.txt 已更新"
        git add requirements.txt
    fi
}

# 读取版本历史记录函数
read_version_history() {
    local history_file="version_history"
    if [ -f "$history_file" ]; then
        cat "$history_file"
    fi
}

# 显示历史记录函数
show_version_history() {
    print_step "查看提交历史记录..."
    
    local history_content=$(read_version_history)
    if [ -z "$history_content" ]; then
        print_info "暂无历史记录"
        return
    fi
    
    print_info "最近10次提交记录："
    echo -e "${CYAN}----------------------------------------${NC}"
    echo "$history_content" | tail -n 10 | while IFS='|' read -r timestamp version_tag commit_msg; do
        if [ -n "$timestamp" ]; then
            echo -e "${YELLOW}时间:${NC} $timestamp"
            if [ -n "$version_tag" ] && [ "$version_tag" != "无" ]; then
                echo -e "${GREEN}版本:${NC} $version_tag"
            fi
            echo -e "${BLUE}信息:${NC} $commit_msg"
            echo -e "${CYAN}----------------------------------------${NC}"
        fi
    done
}

# 保存版本历史记录函数
save_version_history() {
    local version_tag="$1"
    local commit_message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local history_file="version_history"
    
    # 如果版本标识为空，设置为"无"
    if [ -z "$version_tag" ]; then
        version_tag="无"
    fi
    
    # 保存记录格式：时间戳|版本标识|提交信息
    echo "$timestamp|$version_tag|$commit_message" >> "$history_file"
    
    # 只保留最近50条记录，避免文件过大
    if [ -f "$history_file" ]; then
        tail -n 50 "$history_file" > "${history_file}.tmp"
        mv "${history_file}.tmp" "$history_file"
    fi
    
    print_info "历史记录已保存"
}

# 获取用户版本标识函数
get_version_tag() {
    print_step "版本标识设置..."
    
    # 显示历史记录
    show_version_history
    
    # 读取上次的版本标识
    local last_version=""
    if [ -f ".last_version" ]; then
        last_version=$(cat .last_version 2>/dev/null | tr -d '\n\r')
    fi
    
    # 显示上次版本信息
    if [ -n "$last_version" ]; then
        print_info "上次版本标识: $last_version"
    else
        print_info "这是首次设置版本标识"
    fi
    
    echo -e "${CYAN}请选择操作：${NC}"
    echo "1) 输入版本标识（如：v1.2.3, release-2024, hotfix-001）"
    echo "2) 跳过版本标识"
    echo -n "请输入选择 [1/2]: "
    
    read -r choice
    
    case $choice in
        1)
            echo -n "请输入版本标识: "
            read -r version_tag
            if [ -n "$version_tag" ]; then
                print_success "版本标识设置为: $version_tag"
                # 保存当前版本标识到项目文件
                echo "$version_tag" > .version_tag
                print_info "版本标识已保存到 .version_tag 文件"
                git add .version_tag
                # 保存到历史记录文件（用于下次提示）
                echo "$version_tag" > .last_version
                # 将版本标识存储到全局变量，供后续保存历史记录使用
                CURRENT_VERSION_TAG="$version_tag"
                print_info "全局变量 CURRENT_VERSION_TAG 设置为: $CURRENT_VERSION_TAG"
                return 0
            else
                print_warning "版本标识为空，跳过设置"
                CURRENT_VERSION_TAG=""
            fi
            ;;
        2)
            print_info "跳过版本标识设置"
            CURRENT_VERSION_TAG=""
            ;;
        *)
            print_warning "无效选择，跳过版本标识设置"
            CURRENT_VERSION_TAG=""
            ;;
    esac
}

# Git 提交和推送函数
commit_and_push() {
    print_step "准备 Git 提交..."
    
    # 清理已跟踪但应被忽略的文件
    print_info "清理缓存文件..."
    git rm -r --cached __pycache__/ 2>/dev/null || true
    git rm -r --cached FPLP/ 2>/dev/null || true
    git rm --cached .last_version 2>/dev/null || true
    
    # 检查是否有变化
    if git diff --quiet && git diff --cached --quiet; then
        print_warning "没有检测到文件变化，无需提交"
        return 0
    fi
    
    # 显示变化的文件
    print_info "检测到以下文件变化："
    git status --porcelain
    
    # 添加所有变化的文件（排除忽略的文件）
    print_info "添加所有变化的文件..."
    git add .
    
    # 获取提交信息
    echo -n "请输入提交信息（回车使用默认信息）: "
    read -r commit_message
    
    if [ -z "$commit_message" ]; then
        commit_message="自动提交: $(date '+%Y-%m-%d %H:%M:%S')"
    fi
    
    # 提交变化
    print_info "提交变化..."
    if git commit -m "$commit_message"; then
        print_success "提交成功: $commit_message"
        
        # 读取当前版本标识（如果存在 .version_tag 文件）
        local current_version=""
        if [ -f ".version_tag" ]; then
            current_version=$(cat .version_tag 2>/dev/null | tr -d '\n\r')
        fi
        
        # 如果全局变量为空，使用文件中的版本标识
        if [ -z "$CURRENT_VERSION_TAG" ] && [ -n "$current_version" ]; then
            CURRENT_VERSION_TAG="$current_version"
        fi
        
        # 保存历史记录
        print_info "准备保存历史记录，当前版本标识: '$CURRENT_VERSION_TAG'"
        save_version_history "$CURRENT_VERSION_TAG" "$commit_message"
        
        # 将历史记录文件添加到 Git（如果有更新）
        if [ -f "version_history" ]; then
            git add version_history
            git commit -m "更新版本历史记录" --quiet || true
        fi
    else
        handle_error "提交失败"
    fi
    
    # 推送到远程仓库
    print_info "推送到远程仓库..."
    if git push origin $(git branch --show-current); then
        print_success "推送成功"
    else
        print_error "推送失败，请检查网络连接和权限"
        echo -e "${YELLOW}提示：${NC}如果是首次推送，可能需要设置上游分支："
        echo "git push --set-upstream origin $(git branch --show-current)"
        exit 1
    fi
}

# 主函数
main() {
    print_info "开始执行 Git 同步推送流程..."
    echo "=================================="
    
    # 检查必要的命令
    check_command "git"
    check_command "python"
    
    # 确保在 Git 仓库中
    if [ ! -d ".git" ]; then
        handle_error "当前目录不是 Git 仓库"
    fi
    
    # 执行各个步骤
    check_python_syntax
    check_bash_syntax
    activate_virtual_env
    update_requirements
    get_version_tag
    commit_and_push
    
    echo "=================================="
    print_success "Git 同步推送流程完成！"
}

# 脚本入口点
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
