/*
 *  Copyright (c) 2024 Fraunhofer-Gesellschaft zur Förderung der angewandten Forschung e.V.
 *
 *  This program and the accompanying materials are made available under the
 *  terms of the Apache License, Version 2.0 which is available at
 *  https://www.apache.org/licenses/LICENSE-2.0
 *
 *  SPDX-License-Identifier: Apache-2.0
 *
 *  Contributors:
 *       Fraunhofer-Gesellschaft zur Förderung der angewandten Forschung e.V. - initial API and implementation
 *
 */

package org.eclipse.edc.sample.extension.policy;

import org.eclipse.edc.connector.controlplane.contract.spi.policy.ContractNegotiationPolicyContext;
import org.eclipse.edc.policy.engine.spi.PolicyEngine;
import org.eclipse.edc.policy.engine.spi.RuleBindingRegistry;
import org.eclipse.edc.policy.model.Permission;
import org.eclipse.edc.runtime.metamodel.annotation.Inject;
import org.eclipse.edc.spi.system.ServiceExtension;
import org.eclipse.edc.spi.system.ServiceExtensionContext;

import static org.eclipse.edc.connector.controlplane.contract.spi.policy.ContractNegotiationPolicyContext.NEGOTIATION_SCOPE;
import static org.eclipse.edc.jsonld.spi.PropertyAndTypeNames.ODRL_USE_ACTION_ATTRIBUTE;
import static org.eclipse.edc.policy.engine.spi.PolicyEngine.ALL_SCOPES;
import static org.eclipse.edc.spi.constants.CoreConstants.EDC_NAMESPACE;

public class PolicyFunctionsExtension implements ServiceExtension {
    // 简单复杂度：地点约束
    private static final String LOCATION_CONSTRAINT_KEY = EDC_NAMESPACE + "location";
    
    // 中等复杂度：时间范围约束
    private static final String TIME_RANGE_CONSTRAINT_KEY = EDC_NAMESPACE + "timeRange";
    
    // 高复杂度：数据保护级别约束
    private static final String DATA_PROTECTION_LEVEL_CONSTRAINT_KEY = EDC_NAMESPACE + "dataProtectionLevel";
    
    @Inject
    private RuleBindingRegistry ruleBindingRegistry;
    @Inject
    private PolicyEngine policyEngine;
    
    @Override
    public String name() {
        return "Sample policy functions - Multiple complexity levels";
    }
    
    @Override
    public void initialize(ServiceExtensionContext context) {
        var monitor = context.getMonitor();
        
        // 注册基础约束（适用于所有scope）
        ruleBindingRegistry.bind(ODRL_USE_ACTION_ATTRIBUTE, ALL_SCOPES);
        
        // 简单级别：地点约束 (Simple - Location-based)
        ruleBindingRegistry.bind(LOCATION_CONSTRAINT_KEY, NEGOTIATION_SCOPE);
        policyEngine.registerFunction(ContractNegotiationPolicyContext.class, Permission.class, 
                LOCATION_CONSTRAINT_KEY, new LocationConstraintFunction(monitor));
        monitor.info("Registered LocationConstraintFunction - Simple complexity level");
        
        // 中等级别：时间范围约束 (Medium - Time-based)
        ruleBindingRegistry.bind(TIME_RANGE_CONSTRAINT_KEY, NEGOTIATION_SCOPE);
        policyEngine.registerFunction(ContractNegotiationPolicyContext.class, Permission.class, 
                TIME_RANGE_CONSTRAINT_KEY, new TimeRangeConstraintFunction(monitor));
        monitor.info("Registered TimeRangeConstraintFunction - Medium complexity level");
        
        // 高级别：数据保护级别约束 (Advanced - Multi-level data protection)
        ruleBindingRegistry.bind(DATA_PROTECTION_LEVEL_CONSTRAINT_KEY, NEGOTIATION_SCOPE);
        policyEngine.registerFunction(ContractNegotiationPolicyContext.class, Permission.class, 
                DATA_PROTECTION_LEVEL_CONSTRAINT_KEY, new DataProtectionLevelConstraintFunction(monitor));
        monitor.info("Registered DataProtectionLevelConstraintFunction - Advanced complexity level");
    }
}