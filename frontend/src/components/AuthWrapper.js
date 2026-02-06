import React from 'react';
import { Authenticator } from '@aws-amplify/ui-react';
import '@aws-amplify/ui-react/styles.css';
import { Alert } from 'antd';

const AuthWrapper = ({ children }) => {
  const formFields = {
    signUp: {
      email: {
        order: 1,
        placeholder: '请输入邮箱',
        label: '邮箱',
        isRequired: true,
      },
      password: {
        order: 2,
        placeholder: '请输入密码（至少8位，包含大小写字母和数字）',
        label: '密码',
        isRequired: true,
      },
      confirm_password: {
        order: 3,
        placeholder: '请再次输入密码',
        label: '确认密码',
        isRequired: true,
      },
      name: {
        order: 4,
        placeholder: '请输入姓名',
        label: '姓名',
        isRequired: true,
      },
    },
  };

  const components = {
    SignUp: {
      FormFields() {
        return (
          <>
            <Alert
              message="注册须知"
              description="注册后需要管理员审批才能访问系统。审批通过后您将收到邮件通知。"
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
            <Authenticator.SignUp.FormFields />
          </>
        );
      },
    },
  };

  return (
    <Authenticator
      formFields={formFields}
      components={components}
      signUpAttributes={['email', 'name']}
    >
      {({ signOut, user }) => children({ signOut, user })}
    </Authenticator>
  );
};

export default AuthWrapper;
