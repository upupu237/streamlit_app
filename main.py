import streamlit as st
import sys
import os
import matplotlib.pyplot as plt
from text.Interview_test import InterviewSystem, start_interview
from text.ResumeEvaluator import display_resume_evaluation
from text.UserManager import UserManager
from text.resume_editor import resume_management

# 获取当前脚本(main.py)所在目录的绝对路径
project_root = os.path.dirname(os.path.abspath(__file__))
print(f"项目根目录: {project_root}")
# 将项目根目录添加到系统路径
sys.path.append(project_root)

# 导入音频功能核心函数
from audio.streamlit_app import show_audio_app
# 导入视频功能核心函数
from video.app import show_video_app

# 确保中文显示正常
plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC"]
plt.rcParams['axes.unicode_minus'] = False

# 讯飞星火X1 API配置
APPID = "79be4290"
APIKey = "867eb662349b45edf64a4d48bc638a62"
APISecret = "ZjE5NTZiYWFmNWNlMjg0OTUzMWVlM2Uz"
DOMAIN = "x1"
SPARK_URL = "wss://spark-api.xf-yun.com/v1/x1"

# 文件夹配置
UPLOAD_FOLDER = 'audio/uploads'
PCM_FOLDER = 'audio/pcm_files'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PCM_FOLDER, exist_ok=True)

# 初始化会话状态函数
def init_session_state():
    """统一初始化所有会话状态变量，包括选择状态"""
    if 'user_manager' not in st.session_state:
        st.session_state.user_manager = UserManager()
    if 'interview_system' not in st.session_state:
        st.session_state.interview_system = InterviewSystem()
    if 'current_user' not in st.session_state:
        st.session_state.current_user = None
    # 新增：保存当前选择的功能模块
    if 'current_selection' not in st.session_state:
        st.session_state.current_selection = "首页"  # 默认首页
    # 其他原有状态初始化...
    if 'current_questions' not in st.session_state:
        st.session_state.current_questions = []
    if 'user_answers' not in st.session_state:
        st.session_state.user_answers = []
    if 'current_job' not in st.session_state:
        st.session_state.current_job = None
    if 'interview_questions' not in st.session_state:
        st.session_state.interview_questions = []
    if 'generated_intro' not in st.session_state:
        st.session_state.generated_intro = None
    if 'practice_history' not in st.session_state:
        st.session_state.practice_history = {}

# 主应用
def main():
    st.set_page_config(
        page_title="智能面试系统",
        page_icon="📝",
        layout="wide"
    )

    # 初始化会话状态（包含选择状态）
    init_session_state()


    # 侧边栏导航（用会话状态保存选择）
    st.sidebar.title("智能面试系统")

    # 根据登录状态确定菜单项
    if st.session_state.current_user:
        menu_options = [
            "首页", "简历管理", "简历评价", "开始笔试", "笔试历史",
            "音频分析综合功能",
            "视频分析综合功能", "退出登录"
        ]
    else:
        menu_options = ["首页", "登录", "注册"]

    # 关键修改：确保current_selection在当前菜单中，否则重置为首页
    if st.session_state.current_selection not in menu_options:
        st.session_state.current_selection = "首页"
        print(f"会话状态中的选择不在当前菜单中，已重置为首页")

    # 从会话状态获取上次选择，保持状态
    selection = st.sidebar.radio(
        "",
        menu_options,
        index=menu_options.index(st.session_state.current_selection)  # 确保不会报错
    )

    # 保存当前选择到会话状态
    st.session_state.current_selection = selection

    # 调试输出：打印当前选择，验证是否正确
    st.write(f"当前选择的功能模块: {selection}")
    print(f"控制台输出 - 当前选择: {selection}")

    # 导航逻辑实现
    if selection == "首页":
        st.title("智能面试系统")
        st.markdown("""
        欢迎使用智能面试系统！本系统提供以下功能：
        - 用户注册与登录
        - 简历上传与解析
        - 简历评价与优化建议
        - 岗位笔试评估
        - 音频面试分析
        - 视频面试与姿态分析
        """)
        if st.session_state.current_user:
            st.subheader("笔试概览")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("笔试岗位数", len(st.session_state.interview_system.job_data))
            with col2:
                total_questions = sum(len(jobs) for jobs in st.session_state.interview_system.job_data.values())
                st.metric("笔试总问题数", total_questions)
            with col3:
                user = st.session_state.user_manager.users.get(st.session_state.current_user, {})
                history_count = len(user.get("interview_history", []))
                st.metric("历史已完成笔试", history_count)

    elif selection == "音频分析综合功能":
        st.write("进入音频分析综合功能分支")
        print("控制台输出 - 进入音频分析综合功能分支")

        try:
            show_audio_app()
        except Exception as e:
            st.error(f"音频分析功能加载失败: {str(e)}")
            st.code(f"详细错误: {e}", language="text")

    elif selection == "视频分析综合功能":
        st.write("进入视频分析综合功能分支")
        print("控制台输出 - 进入视频分析综合功能分支")

        try:
            show_video_app()
        except Exception as e:
            st.error(f"视频分析功能加载失败: {str(e)}")
            st.code(f"详细错误: {e}", language="text")

    elif selection == "注册":
        st.title("用户注册")
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")
        confirm_password = st.text_input("确认密码", type="password")

        if st.button("注册"):
            if not username or not password:
                st.error("用户名和密码不能为空")
            elif password != confirm_password:
                st.error("两次输入的密码不一致")
            else:
                success, message = st.session_state.user_manager.register_user(username, password)
                if success:
                    st.success(message)
                    st.balloons()
                    st.info("注册成功，请登录")
                else:
                    st.error(message)

    elif selection == "登录":
        st.title("用户登录")
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")

        if st.button("登录"):
            success, message = st.session_state.user_manager.login_user(username, password)
            if success:
                st.success(message)
                st.session_state.current_user = username
                # 关键修改：登录成功后重置选择为首页
                st.session_state.current_selection = "首页"
                st.rerun()
            else:
                st.error(message)

    elif selection == "退出登录":
        st.title("退出登录")
        if st.button("确认退出"):
            st.session_state.current_user = None
            # 关键修改：退出登录后重置选择为首页
            st.session_state.current_selection = "首页"
            st.success("已成功退出登录")
            st.rerun()

    elif selection == "简历管理":
        st.write("进入个人简历管理功能分支")
        print("控制台输出 -进入个人简历管理功能分支")
        try:
            resume_management()
        except Exception as e:
            st.error(f"简历管理功能加载失败: {str(e)}")
            st.code(f"详细错误: {e}", language="text")

    elif selection == "简历评价":
        st.write("进入个人简历评价功能分支")
        session_state = st.session_state
        print("控制台输出 -进入个人简历评价功能分支")
        try:
            display_resume_evaluation(st, session_state)
        except Exception as e:
            st.error(f"简历评价功能加载失败: {str(e)}")
            st.code(f"详细错误: {e}", language="text")

    elif selection == "开始笔试":
        st.write("进入笔试功能分支")
        print("控制台输出 -进入笔试功能分支")
        try:
            start_interview()
        except Exception as e:
            st.error(f"进入笔试功能加载失败: {str(e)}")
            st.code(f"详细错误: {e}", language="text")

    elif selection == "笔试历史":
        st.title("笔试历史")
        user = st.session_state.current_user
        # 获取用户面试历史
        user_data = st.session_state.user_manager.users.get(user, {})
        history = user_data.get("interview_history", [])
        if not history:
            st.info("您还没有完成任何笔试")
        else:
            # 显示面试历史表格
            st.subheader("笔试记录")
            for i, entry in enumerate(history, 1):
                with st.expander(f"笔试 {i}: {entry['job']} - {entry['time']}"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("正确率", f"{entry['score'] * 100:.2f}%")
                    with col2:
                        st.metric("专业知识水平", entry['level'])
                    with col3:
                        st.metric("技能匹配度", entry['match'])
                    # 显示雷达图
                    fig = st.session_state.interview_system.generate_radar_chart(entry['score'], entry['level'])
                    st.pyplot(fig)


if __name__ == "__main__":
    main()