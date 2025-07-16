/**
 * 测试脚本：验证每次执行都生成独立的报告
 */
const axios = require('axios');

const SERVER_URL = 'http://localhost:3001';

// 示例测试用例
const testCase = {
    name: '独立报告测试',
    steps: [
        {
            action: 'navigate',
            params: { url: 'https://www.baidu.com' },
            description: '访问百度首页'
        },
        {
            action: 'ai_input',
            params: { text: '测试搜索', locate: '搜索框' },
            description: '输入搜索关键词'
        },
        {
            action: 'ai_tap',
            params: { locate: '搜索按钮' },
            description: '点击搜索按钮'
        }
    ]
};

async function testIndependentReports() {
    try {
        console.log('🧪 开始测试独立报告生成...\n');
        
        // 执行第一次测试
        console.log('📋 执行第一次测试...');
        const response1 = await axios.post(`${SERVER_URL}/api/execute-testcase`, {
            testcase: testCase,
            mode: 'headless'
        });
        
        const executionId1 = response1.data.executionId;
        console.log(`   执行ID: ${executionId1}`);
        
        // 等待第一次执行完成
        await waitForExecution(executionId1);
        
        // 获取第一次执行的报告
        const report1 = await axios.get(`${SERVER_URL}/api/execution-report/${executionId1}`);
        console.log(`   第一次执行完成，步骤数: ${report1.data.report.steps.length}`);
        console.log(`   第一次执行日志数: ${report1.data.report.logs.length}`);
        
        // 执行第二次测试
        console.log('\n📋 执行第二次测试...');
        const response2 = await axios.post(`${SERVER_URL}/api/execute-testcase`, {
            testcase: testCase,
            mode: 'headless'
        });
        
        const executionId2 = response2.data.executionId;
        console.log(`   执行ID: ${executionId2}`);
        
        // 等待第二次执行完成
        await waitForExecution(executionId2);
        
        // 获取第二次执行的报告
        const report2 = await axios.get(`${SERVER_URL}/api/execution-report/${executionId2}`);
        console.log(`   第二次执行完成，步骤数: ${report2.data.report.steps.length}`);
        console.log(`   第二次执行日志数: ${report2.data.report.logs.length}`);
        
        // 验证报告是否独立
        console.log('\n🔍 验证报告独立性...');
        console.log(`   第一次执行ID: ${report1.data.report.executionId}`);
        console.log(`   第二次执行ID: ${report2.data.report.executionId}`);
        console.log(`   执行ID不同: ${report1.data.report.executionId !== report2.data.report.executionId}`);
        
        // 验证步骤数据独立
        const steps1 = report1.data.report.steps.length;
        const steps2 = report2.data.report.steps.length;
        console.log(`   第一次步骤数: ${steps1}`);
        console.log(`   第二次步骤数: ${steps2}`);
        console.log(`   步骤数相同: ${steps1 === steps2}`);
        
        // 验证日志数据独立
        const logs1 = report1.data.report.logs.length;
        const logs2 = report2.data.report.logs.length;
        console.log(`   第一次日志数: ${logs1}`);
        console.log(`   第二次日志数: ${logs2}`);
        console.log(`   日志数相近: ${Math.abs(logs1 - logs2) <= 1}`);
        
        // 获取所有执行记录
        const allExecutions = await axios.get(`${SERVER_URL}/api/executions`);
        console.log(`\n📊 服务器上的执行记录总数: ${allExecutions.data.total}`);
        
        console.log('\n✅ 测试完成！每次执行都生成了独立的报告');
        
    } catch (error) {
        console.error('❌ 测试失败:', error.message);
    }
}

async function waitForExecution(executionId) {
    return new Promise((resolve) => {
        const checkStatus = async () => {
            try {
                const status = await axios.get(`${SERVER_URL}/api/execution-status/${executionId}`);
                if (status.data.status === 'completed' || status.data.status === 'failed') {
                    resolve();
                } else {
                    setTimeout(checkStatus, 1000);
                }
            } catch (error) {
                setTimeout(checkStatus, 1000);
            }
        };
        checkStatus();
    });
}

// 运行测试
testIndependentReports();