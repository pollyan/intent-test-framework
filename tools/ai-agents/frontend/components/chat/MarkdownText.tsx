/**
 * MarkdownText 组件 - 使用 Assistant-ui 的 Markdown 渲染
 */
import { memo } from 'react';
import { MarkdownTextPrimitive } from '@assistant-ui/react-markdown';
import remarkGfm from 'remark-gfm';

// 创建基础 MarkdownText 组件
const MarkdownTextImpl = () => {
    return (
        <MarkdownTextPrimitive
            remarkPlugins={[remarkGfm]}
            className="prose prose-sm dark:prose-invert max-w-none break-words"
        />
    );
};

export const MarkdownText = memo(MarkdownTextImpl);

export default MarkdownText;
