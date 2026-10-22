import React, { useCallback, useState } from 'react';
import { Upload, message } from 'antd';
import { InboxOutlined } from '@ant-design/icons';
import type { UploadProps } from 'antd/es/upload/interface';

const { Dragger } = Upload;

interface FileUploadProps {
  onUpload: (file: File) => Promise<void> | void;
  accept?: string;
  maxSizeMB?: number;
  multiple?: boolean;
  tip?: string;
}

/**
 * 文件拖拽上传组件
 */
const FileUpload: React.FC<FileUploadProps> = ({
  onUpload,
  accept = '.txt,.md,.pdf,.docx,.doc',
  maxSizeMB = 10,
  multiple = false,
  tip,
}) => {
  const [uploading, setUploading] = useState(false);

  const beforeUpload = useCallback((file: File) => {
    const maxSize = maxSizeMB * 1024 * 1024;
    if (file.size > maxSize) {
      message.error(`文件大小不能超过 ${maxSizeMB}MB`);
      return Upload.LIST_IGNORE;
    }
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (accept && !accept.split(',').some(a => a.trim() === ext || a.trim() === '*')) {
      message.error(`不支持的文件类型，请上传 ${accept} 格式的文件`);
      return Upload.LIST_IGNORE;
    }
    return true;
  }, [accept, maxSizeMB]);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const customRequest = useCallback(async (options: any) => {
    setUploading(true);
    try {
      await onUpload(options.file as File);
      options.onSuccess?.(undefined, new XMLHttpRequest());
      message.success('上传成功');
    } catch (err) {
      options.onError?.(err as Error);
      message.error('上传失败：' + (err as Error).message);
    } finally {
      setUploading(false);
    }
  }, [onUpload]);

  const props: UploadProps = {
    name: 'file',
    multiple,
    accept,
    beforeUpload,
    customRequest,
    showUploadList: false,
    disabled: uploading,
  };

  return (
    <Dragger {...props}>
      <p className="ant-upload-drag-icon">
        <InboxOutlined />
      </p>
      <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
      <p className="ant-upload-hint">
        {tip || `支持 ${accept} 格式，单个文件不超过 ${maxSizeMB}MB`}
      </p>
    </Dragger>
  );
};

export default FileUpload;
