import { IconCheck, IconCut, IconX } from '@tabler/icons-react';
import { FC, useState } from 'react';
import { useTranslation } from 'react-i18next';

interface Props {
  onSplitConversation: () => void;
}

export const SplitConversation: FC<Props> = ({ onSplitConversation }) => {
  const [isConfirming, setIsConfirming] = useState<boolean>(false);

  const { t } = useTranslation('sidebar');

  const handleClearConversations = () => {
    onSplitConversation();
    setIsConfirming(false);
  };

  return isConfirming ? (
    <div className="flex w-full cursor-pointer items-center rounded-lg hover:bg-gray-100">
      <div className="flex w-[40px]">
        <IconCheck
          className="ml-auto mr-1 min-w-[20px] hover:text-green-500"
          size={18}
          onClick={(e) => {
            e.stopPropagation();
            handleClearConversations();
          }}
        />

        <IconX
          className="ml-auto min-w-[20px] hover:text-red-500"
          size={18}
          onClick={(e) => {
            e.stopPropagation();
            setIsConfirming(false);
          }}
        />
      </div>
    </div>
  ) : (
    <button
      className="invisible group-hover:visible focus:visible text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
      onClick={() => setIsConfirming(true)}
    >
      <IconCut size={20} />
    </button>
  );
};
