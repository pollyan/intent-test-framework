import React from 'react';
import { Menu, ChevronDown, Mail, Smartphone, Globe, FileText, Github } from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <>
      <header className="bg-surface-light dark:bg-surface-dark border-b border-border-light dark:border-border-dark sticky top-0 z-50 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex-shrink-0 flex items-center">
              <span className="font-bold text-xl tracking-tight text-gray-900 dark:text-white">
                老兵大头的 AI4SE 工具集
              </span>
            </div>
            <nav className="hidden md:flex space-x-8">
              <a href="#" className="relative text-gray-900 dark:text-white font-medium hover:text-primary transition-colors flex flex-col items-center group">
                首页
                <span className="absolute -bottom-5 w-full h-0.5 bg-gray-900 dark:bg-white rounded-t-lg group-hover:bg-primary transition-colors"></span>
              </a>
              <div className="relative group">
                <button className="text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white inline-flex items-center font-medium transition-colors">
                  <span>意图测试工具</span>
                  <ChevronDown className="ml-1 w-4 h-4" />
                </button>
              </div>
              <div className="relative group">
                <button className="text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white inline-flex items-center font-medium transition-colors">
                  <span>AI智能体们</span>
                  <ChevronDown className="ml-1 w-4 h-4" />
                </button>
              </div>
              <a href="#" className="text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white font-medium transition-colors">
                个人简介
              </a>
            </nav>
            <div className="md:hidden flex items-center">
              <button className="text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white p-2 rounded-md">
                <Menu className="w-6 h-6" />
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="flex-grow max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full">
        {children}
      </main>

      <footer className="bg-gray-50 dark:bg-gray-900 border-t border-border-light dark:border-border-dark mt-auto pt-12 pb-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-8">
            <div>
              <h3 className="flex items-center text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wider mb-4">
                <span className="text-lg mr-2">👨‍💻</span> 关于作者
              </h3>
              <div className="text-sm text-gray-600 dark:text-gray-400 space-y-3">
                <p className="font-medium">由 安辉（老兵大头） 独立开发与维护</p>
                <p>19年研发经验 | AI4SE 实践者 | ThoughtWorks校友</p>
                <p className="leading-relaxed text-xs">
                  作为一名在软件工程领域深耕近 20 年的老兵，致力于将 AI 技术转化为企业级生产力工具。如果这些工具对你有帮助，欢迎反馈和交流！
                </p>
              </div>
            </div>
            <div className="md:pl-10">
              <h3 className="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wider mb-4">
                快速链接
              </h3>
              <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                <li><a href="#" className="hover:text-primary transition-colors">首页</a></li>
                <li><a href="#" className="hover:text-primary transition-colors">意图测试工具</a></li>
                <li><a href="#" className="hover:text-primary transition-colors">AI智能助手</a></li>
                <li><a href="#" className="hover:text-primary transition-colors">个人简介</a></li>
                <li><a href="#" className="hover:text-primary transition-colors">GitHub 仓库</a></li>
              </ul>
            </div>
            <div>
              <h3 className="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wider mb-4">
                联系方式
              </h3>
              <ul className="space-y-3 text-sm text-gray-600 dark:text-gray-400">
                <li className="flex items-center">
                  <Mail className="text-gray-400 mr-2 w-4 h-4" />
                  <a href="mailto:pollyan@163.com" className="hover:text-primary transition-colors border-b border-dotted border-gray-400">pollyan@163.com</a>
                </li>
                <li className="flex items-center">
                  <Smartphone className="text-gray-400 mr-2 w-4 h-4" />
                  <span>18910027087</span>
                </li>
                <li className="flex items-center">
                  <Globe className="text-gray-400 mr-2 w-4 h-4" />
                  <a href="#" className="hover:text-primary transition-colors">个人简介</a>
                </li>
                <li className="flex items-center">
                  <FileText className="text-gray-400 mr-2 w-4 h-4" />
                  <a href="#" className="hover:text-primary transition-colors">技术文章</a>
                </li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-200 dark:border-gray-800 pt-8 text-center text-xs text-gray-500 dark:text-gray-500 space-y-2">
            <p>© 2024 老兵大头的 AI4SE 工具集 | 基于 MIT 协议开源</p>
            <p>让 AI 驱动的软件工程变得简单而强大</p>
          </div>
        </div>
      </footer>
    </>
  );
};

export default Layout;