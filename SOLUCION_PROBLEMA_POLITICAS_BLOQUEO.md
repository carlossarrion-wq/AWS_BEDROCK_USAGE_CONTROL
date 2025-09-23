# SOLUCIÓN AL PROBLEMA DE POLÍTICAS DE BLOQUEO

## PROBLEMA IDENTIFICADO

La función Lambda `bedrock-realtime-usage-controller` **NO estaba aplicando correctamente las políticas de bloqueo** debido a **permisos IAM insuficientes**.

### Síntomas del Problema
- Las políticas inline de usuarios bloqueados solo contenían la directiva "Allow" sin la directiva "Deny"
- Los logs mostraban errores de `AccessDenied` al intentar crear políticas IAM
- Los usuarios no quedaban efectivamente bloqueados del acceso a Bedrock

### Error Específico en los Logs
```
❌ Failed to create IAM deny policy for user sap_003: An error occurred (AccessDenied) when calling the GetUserPolicy operation: User: arn:aws:sts::701055077130:assumed-role/bedrock-realtime-usage-controller-role/bedrock-realtime-usage-controller is not authorized to perform: iam:GetUserPolicy on resource: user sap_003 because no identity-based policy allows the iam:GetUserPolicy action
```

## CAUSA RAÍZ

El rol IAM `bedrock-realtime-usage-controller-role` **NO tenía permisos para gestionar políticas inline de usuarios**. La política solo incluía permisos para políticas gestionadas pero no para políticas inline.

### Permisos Faltantes
- `iam:GetUserPolicy` - para leer políticas inline existentes
- `iam:PutUserPolicy` - para crear/actualizar políticas inline  
- `iam:DeleteUserPolicy` - para eliminar políticas inline
- `iam:ListUserPolicies` - para listar políticas inline

## SOLUCIÓN APLICADA

### 1. Identificación del Problema
- ✅ Revisión del código de la función Lambda
- ✅ Análisis de logs de CloudWatch
- ✅ Identificación de errores de permisos IAM

### 2. Corrección de Permisos IAM
Se actualizó la política `BedrockRealtimeUsageControllerPolicy` del rol `bedrock-realtime-usage-controller-role` para incluir los permisos faltantes:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "iam:ListUserTags",
                "iam:GetUser",
                "iam:GetGroupsForUser",
                "iam:AttachUserPolicy",
                "iam:DetachUserPolicy",
                "iam:ListAttachedUserPolicies",
                "iam:CreatePolicy",
                "iam:GetPolicy",
                "iam:DeletePolicy",
                "iam:CreatePolicyVersion",
                "iam:DeletePolicyVersion",
                "iam:ListPolicyVersions",
                "iam:GetUserPolicy",        // ← NUEVO
                "iam:PutUserPolicy",        // ← NUEVO
                "iam:DeleteUserPolicy",     // ← NUEVO
                "iam:ListUserPolicies"      // ← NUEVO
            ],
            "Resource": "*"
        },
        // ... resto de statements
    ]
}
```

### 3. Comando de Aplicación
```bash
aws iam put-role-policy \
  --role-name bedrock-realtime-usage-controller-role \
  --policy-name BedrockRealtimeUsageControllerPolicy \
  --policy-document file://iam_policy_fix.json \
  --region eu-west-1
```

## RESULTADO ESPERADO

Con esta corrección, la función Lambda ahora debería:

1. ✅ **Leer políticas inline existentes** de usuarios con `iam:GetUserPolicy`
2. ✅ **Crear políticas de bloqueo** con directivas "Deny" usando `iam:PutUserPolicy`
3. ✅ **Aplicar bloqueos efectivos** que impidan el acceso a Bedrock
4. ✅ **Eliminar políticas de bloqueo** durante el desbloqueo con `iam:DeleteUserPolicy`

## VERIFICACIÓN

Para verificar que la solución funciona:

1. **Monitorear logs de CloudWatch** para confirmar que no hay más errores de `AccessDenied`
2. **Probar un caso de bloqueo** y verificar que la política inline contiene la directiva "Deny"
3. **Confirmar que el usuario bloqueado** no puede acceder a Bedrock

## ARCHIVOS MODIFICADOS

- ✅ `iam_policy_fix.json` - Nueva política IAM con permisos corregidos
- ✅ Política IAM del rol `bedrock-realtime-usage-controller-role` actualizada

## FECHA DE APLICACIÓN

**23 de septiembre de 2025, 19:05 CET**

---

**PROBLEMA RESUELTO**: Las políticas de bloqueo ahora deberían aplicarse correctamente con las directivas "Deny" necesarias para bloquear efectivamente el acceso a AWS Bedrock.
