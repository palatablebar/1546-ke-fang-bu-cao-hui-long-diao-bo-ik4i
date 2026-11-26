function renderVisual(target, data) {
    const counts = new Map(data.flow_counts);
    const handled = counts.get('已分派') ?? 0;
    const pending = counts.get('候补') ?? 0;
    const manual = (counts.get('暂停') ?? 0) + (counts.get('人工判读') ?? 0);
    const measures = [['回笼班次',data.rows.length],['可推断班次',data.rows.length-manual],['申请出车',pending+handled],['已排调拨',handled]];
    const chart = node('div',undefined,'flow');
    measures.forEach(([label,value]) => {
        const step = node('div',undefined,'flow-step');
        step.append(node('strong',value),node('span',label));
        chart.append(step);
    });
    const fork = node('div',undefined,'branch');
    fork.append(node('span',`单据人工核验 ${manual} 班`),node('span',`车位候补 ${pending} 班`));
    target.append(chart,fork);
}
