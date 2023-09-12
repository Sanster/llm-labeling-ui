import { IconCheck, IconUsers, IconX } from '@tabler/icons-react';
import { FC, KeyboardEvent, useEffect, useRef, useState } from 'react';

import { useTranslation } from 'next-i18next';

interface Props {
  apiOrg: string;
  onApiOrgChange: (apiOrg: string) => void;
}

export const Org: FC<Props> = ({ apiOrg, onApiOrgChange }) => {
  const { t } = useTranslation('sidebar');
  const [isChanging, setIsChanging] = useState(false);
  const [newOrg, setNewOrg] = useState(apiOrg);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleEnterDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleUpdateKey(newOrg);
    }
  };

  const handleUpdateKey = (newKey: string) => {
    onApiOrgChange(newKey.trim());
    setIsChanging(false);
  };

  useEffect(() => {
    if (isChanging) {
      inputRef.current?.focus();
    }
  }, [isChanging]);

  return isChanging ? (
    <div className="duration:200 flex w-full cursor-pointer items-center rounded-md py-3 px-3 transition-colors hover:bg-gray-500/10 text-black dark:text-neutral-200">
      <IconUsers size={18} />

      <input
        ref={inputRef}
        className="ml-2 h-[20px] flex-1 overflow-hidden overflow-ellipsis border-b border-neutral-400 bg-transparent pr-1 text-[12.5px] leading-3 text-left text-black dark:text-neutral-200 outline-none focus:border-neutral-100"
        // type="text"
        value={newOrg}
        onChange={(e) => setNewOrg(e.target.value)}
        onKeyDown={handleEnterDown}
        placeholder={t('API Organization') || 'API Organization'}
      />

      <div className="flex w-[40px]">
        <IconCheck
          className="ml-auto min-w-[20px] text-neutral-400 hover:text-black"
          size={18}
          onClick={(e) => {
            e.stopPropagation();
            handleUpdateKey(newOrg);
          }}
        />

        <IconX
          className="ml-auto min-w-[20px] text-neutral-400 hover:text-black"
          size={18}
          onClick={(e) => {
            e.stopPropagation();
            setIsChanging(false);
            setNewOrg(apiOrg);
          }}
        />
      </div>
    </div>
  ) : (
    <button
      className="flex w-full cursor-pointer select-none items-center gap-3 rounded-md py-3 px-3 text-[14px] leading-3 text-black dark:text-neutral-200 transition-colors duration-200 hover:bg-gray-500/10"
      onClick={() => setIsChanging(true)}
    >
      <div>{<IconUsers size={18} />}</div>
      <span>{t('OpenAI Organization')}</span>
    </button>
  );
};
